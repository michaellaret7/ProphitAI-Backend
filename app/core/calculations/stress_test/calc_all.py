"""Orchestrator for combined ETF beta-shock stress testing.

Usage:
    result = calc_all_stress_test(
        portfolio_returns=portfolio.daily_returns,
        weights={"AAPL": 0.3, "MSFT": 0.2, ...},
        ticker_returns_map={"AAPL": aapl_returns, "MSFT": msft_returns, ...},
        etf_returns_map={"SPY": spy_returns, "TLT": tlt_returns, "GLD": gld_returns},
        shocks={"SPY": -0.05, "TLT": 0.10, "GLD": -0.04},
    )
"""

from typing import Literal

import numpy as np
import pandas as pd

from app.core.calculations.config import TRADING_DAYS
from app.core.calculations.models.stress_test import StressTestResult
from app.core.calculations.stress_test.calc_stress import (
    calc_etf_contribution,
    calc_factor_vif,
    calc_portfolio_ols,
    calc_ticker_stress_result,
    calc_total_stressed_vol,
)


def calc_all_stress_test(
    portfolio_returns: pd.Series,
    weights: dict[str, float],
    ticker_returns_map: dict[str, pd.Series],
    etf_returns_map: dict[str, pd.Series],
    shocks: dict[str, float],
    top_n: int = 5,
    horizon: Literal["daily"] = "daily",
) -> StressTestResult:
    """Run combined ETF beta-shock stress test on a portfolio.

    Args:
        portfolio_returns: Portfolio-level daily returns (weight-aggregated).
        weights: {ticker: signed weight} — negative = short position.
        ticker_returns_map: {ticker: daily return Series} for each holding.
        etf_returns_map: {ETF: daily return Series} for each factor ETF.
        shocks: {ETF: shock magnitude} — e.g. {"SPY": -0.05, "TLT": 0.10}.
        top_n: Number of top detractors/hedges to return.
        horizon: Time-frame assumption for the stress test.

    Returns:
        StressTestResult with portfolio metrics, per-ticker, and per-ETF breakdowns.
    """
    # ---- Step 1: Per-ticker stress results (bottom-up) ----
    ticker_results = [
        calc_ticker_stress_result(ticker, weight, ticker_returns_map[ticker], etf_returns_map, shocks)
        for ticker, weight in weights.items()
        if ticker in ticker_returns_map
    ]

    # ---- Step 2: Bottom-up expected return (sum of per-ticker weighted PnLs) ----
    valid_pnls = [r.weighted_pnl for r in ticker_results if r.weighted_pnl is not None]
    expected_return_bottom_up = sum(valid_pnls) if valid_pnls else None

    # ---- Step 3: Per-ticker pct_of_portfolio_impact (uses bottom-up for attribution) ----
    if expected_return_bottom_up is not None and expected_return_bottom_up != 0.0:
        for r in ticker_results:
            if r.weighted_pnl is not None:
                r.pct_of_portfolio_impact = round(r.weighted_pnl / expected_return_bottom_up, 4)

    # ---- Step 4: Portfolio-level OLS → top-down expected return, R², residual_std ----
    expected_return: float | None = None
    idiosyncratic_vol_annual: float | None = None
    total_stressed_vol: float | None = None
    stressed_var_95: float | None = None
    r_squared: float | None = None
    residual_std: float | None = None
    portfolio_betas: dict[str, float] = {}

    ols_result = calc_portfolio_ols(portfolio_returns, etf_returns_map)
    if ols_result is not None:
        portfolio_betas, ols_r2, ols_resid_std = ols_result
        r_squared = ols_r2
        residual_std = ols_resid_std
        idiosyncratic_vol_annual = ols_resid_std * np.sqrt(TRADING_DAYS)

        # Reason: top-down expected return = Σ(portfolio_βⱼ × shockⱼ), consistent with residual_std
        expected_return = sum(
            portfolio_betas.get(etf, 0.0) * shock for etf, shock in shocks.items()
        )

        # Reason: VaR uses top-down return and residual_std from same regression
        stressed_var_95 = expected_return - 1.65 * ols_resid_std

        total_stressed_vol = calc_total_stressed_vol(portfolio_betas, etf_returns_map, ols_resid_std)

    # ---- Step 5: Per-ETF contribution (uses top-down betas) ----
    etf_contributions = [
        calc_etf_contribution(
            etf=etf,
            shock=shock,
            portfolio_sensitivity=portfolio_betas.get(etf),
            total_expected=expected_return,
        )
        for etf, shock in shocks.items()
    ]

    # ---- Step 6: Factor collinearity diagnostic (VIF) ----
    factor_vif = calc_factor_vif(etf_returns_map)

    # ---- Step 7: Rank tickers → top detractors + top hedges ----
    scored = [
        (r.ticker, r.weighted_pnl)
        for r in ticker_results
        if r.weighted_pnl is not None
    ]
    scored.sort(key=lambda x: x[1])  # ascending: worst first

    top_detractors = [t for t, _ in scored[:top_n]]
    top_hedges = [t for t, _ in scored[-top_n:][::-1]]  # best first

    return StressTestResult(
        expected_return=expected_return,
        expected_return_bottom_up=expected_return_bottom_up,
        idiosyncratic_vol_annual=idiosyncratic_vol_annual,
        total_stressed_vol=total_stressed_vol,
        stressed_var_95=stressed_var_95,
        r_squared=r_squared,
        residual_std=residual_std,
        horizon=horizon,
        ticker_results=ticker_results,
        etf_contributions=etf_contributions,
        factor_vif=factor_vif,
        top_detractors=top_detractors,
        top_hedges=top_hedges,
    )


if __name__ == "__main__":
    from app.repositories.price_data import fetch_bulk_price_data_for_tickers

    tickers = ['AAPL', 'MSFT', 'NVDA', 'JPM', 'UNH', 'XOM', 'LLY', 'AMZN', 'COST', 'GE', 'TSLA', 'AAL']
    weights = [0.15, 0.12, 0.10, 0.08, 0.08, 0.07, 0.06, 0.06, 0.05, 0.05, 0.09, 0.09]
    holdings = dict(zip(tickers, weights))
    shocks = {'SPY': -0.05, 'TLT': 0.10, 'GLD': -0.04, 'EEM': 0.15}

    price_df = fetch_bulk_price_data_for_tickers(list(holdings) + list(shocks), '2024-01-01', '2026-02-01')
    returns_df = price_df.pct_change(fill_method=None).dropna()

    ticker_rets = {t: returns_df[t] for t in holdings if t in returns_df.columns}
    etf_rets = {e: returns_df[e] for e in shocks}
    port_weights = {t: w for t, w in holdings.items() if t in ticker_rets}
    port_ret = (returns_df[list(port_weights)] * np.array(list(port_weights.values()))).sum(axis=1)

    result = calc_all_stress_test(port_ret, port_weights, ticker_rets, etf_rets, shocks)

    print(result.expected_return)
