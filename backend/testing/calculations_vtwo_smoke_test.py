from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.src.calculations_v2.core import DataService, DataFetchError
from backend.src.calculations_v2.returns import (
    ReturnsCalculator,
    PortfolioReturnsCalculator,
)
from backend.src.calculations_v2.risk import RiskCalculator
from backend.src.calculations_v2.performance import PerformanceCalculator
from backend.src.calculations_v2.factors import (
    ValueFactors,
    GrowthFactors,
    MomentumFactors,
    QualityFactors,
    VolatilityFactors,
)


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_all() -> None:
    ds = DataService()
    now = datetime.now()
    start = now - timedelta(days=365 * 2)
    end = now

    tickers = ["AAPL"]

    rc = ReturnsCalculator()
    rk = RiskCalculator()
    pc = PerformanceCalculator()

    # --------------------------- DataService Checks ---------------------------
    _print_header("Data Fetch (DataService)")
    try:
        aapl_df = ds.get_price_data("AAPL", start, end).frame
        print("fetched AAPL price data:", aapl_df.shape if aapl_df is not None else None)
    except Exception as e:
        print(f"[ERROR] AAPL fetch failed: {e}")
        return

    fundamentals_ok = False
    try:
        f = ds.get_fundamentals("AAPL")
        print(
            "fundamentals[AAPL] -> "
            f"income={len(f.income_statements)}, balance={len(f.balance_sheets)}, "
            f"cashflow={len(f.cash_flow_statements)}, ratios={len(f.financial_ratios)}, "
            f"estimates={len(f.analyst_estimates)}"
        )
        fundamentals_ok = True
    except Exception as e:
        print(f"[WARN] fundamentals fetch failed: {e}")

    # --------------------------- Returns (per ticker) -------------------------
    _print_header("Per-ticker Returns & Risk")
    returns_price_map: dict[str, pd.Series] = {}
    returns_total_map: dict[str, pd.Series] = {}

    close = aapl_df["close"].astype(float)
    try:
        divs = ds.get_dividends("AAPL", start, end).series
    except Exception:
        divs = pd.Series(dtype=float)

    daily_price = rc.daily_price_returns(close)
    daily_total = rc.total_returns(close, divs)

    returns_price_map["AAPL"] = daily_price
    returns_total_map["AAPL"] = daily_total

    ann_ret_total = rc.annualized_return(daily_total)
    ann_vol_total = rk.annualized_volatility(daily_total)

    # Pseudo price for MDD from total returns
    cum = (1 + daily_total).cumprod()
    pseudo_price = cum / (cum.iloc[0] if len(cum) else 1)
    mdd = rk.max_drawdown(pseudo_price)

    # Parametric VaR, Historical VaR, ES
    var_p = rk.parametric_var(annual_vol=ann_vol_total, confidence=0.99)
    var_h = rk.historical_var(daily_total, confidence=0.99)
    es_h = rk.expected_shortfall(daily_total, confidence=0.99)

    print(
        f"AAPL: ann_ret={ann_ret_total:.4f} ann_vol={ann_vol_total:.4f} "
        f"mdd={mdd:.4f} var99(param)={var_p:.4f} var99(hist)={var_h:.4f} es99={es_h:.4f}"
    )

    # --------------------------- Correlation/Covariance -----------------------
    _print_header("Covariance (AAPL only)")
    returns_df = pd.DataFrame(returns_total_map)
    cov_d = rk.covariance_matrix(returns_df, annualize=False)
    cov_a = rk.covariance_matrix(returns_df, annualize=True)
    print("cov_d shape:", getattr(cov_d, "shape", None))
    print("cov_a shape:", getattr(cov_a, "shape", None))

    # --------------------------- Beta vs SPY ----------------------------------
    # Skip beta vs SPY (AAPL only)

    # --------------------------- Portfolio Metrics ---------------------------
    _print_header("AAPL Portfolio Metrics (1-asset)")
    # 1-asset portfolio = AAPL daily total returns
    port_daily = daily_total

    # Returns
    ann_ret_p = rc.annualized_return(port_daily)
    ann_vol_p = rk.annualized_volatility(port_daily)
    cum_p = (1 + port_daily).cumprod()
    pseudo_p = cum_p / (cum_p.iloc[0] if len(cum_p) else 1)
    mdd_p = rk.max_drawdown(pseudo_p)

    # VaR/ES (parametric/historical/MC) + marginal/component VaR
    var99_p = rk.parametric_var(ann_vol_p, 0.99)
    var99_h = rk.historical_var(port_daily, 0.99)
    es99_p = rk.expected_shortfall(port_daily, 0.99)

    # Monte Carlo VaR using daily covariance
    cols = ["AAPL"]
    w_vec = np.array([1.0], dtype=float)
    mc_var = rk.monte_carlo_var(w_vec, returns_df[cols].dropna(), confidence=0.99, n_simulations=5000)

    mv, cv = rk.marginal_var(pd.Series(w_vec, index=cols), cov_d)

    # Performance (full set)
    sharpe = pc.sharpe_ratio(port_daily)
    sortino = pc.sortino_ratio(port_daily)
    calmar = pc.calmar_ratio(ann_ret_p, mdd_p)
    treynor = np.nan
    info = np.nan
    omega = pc.omega_ratio(port_daily)
    sterling = pc.sterling_ratio(ann_ret_p, mdd_p)
    burke = pc.burke_ratio(port_daily)
    martin = pc.martin_ratio(port_daily)
    kappa = pc.kappa_ratio(port_daily)
    alpha = np.nan
    up, down = (np.nan, np.nan)
    win = pc.win_rate(port_daily)
    pf = pc.profit_factor(port_daily)

    print(
        f"portfolio: ann_ret={ann_ret_p:.4f} ann_vol={ann_vol_p:.4f} "
        f"mdd={mdd_p:.4f} var99(param)={var99_p:.4f} var99(hist)={var99_h:.4f} "
        f"es99={es99_p:.4f} mc_var99={mc_var:.4f} "
        f"sharpe={sharpe:.3f} sortino={sortino:.3f} calmar={calmar:.3f} "
        f"treynor={treynor:.3f} info={info:.3f} omega={omega:.3f} sterling={sterling:.3f} "
        f"burke={burke:.3f} martin={martin:.3f} kappa={kappa:.3f} alpha={alpha:.3f} "
        f"up_capture={up:.3f} down_capture={down:.3f} win={win:.3f} profit_factor={pf:.3f}"
    )

    # Position sizing example: given $10k VaR budget
    pos_size = rk.position_size_from_var_budget(var_budget_dollars=10_000, annual_vol=ann_vol_p)
    print(f"position_size_from_var_budget($10k) -> ${pos_size:,.2f}")

    # Print a few marginal/component VaR entries
    print("marginal VaR (head):")
    print(mv.head())
    print("component VaR (head):")
    print(cv.head())

    # --------------------------- Factor Calculations ---------------------------
    _print_header("Factor Calculations (Value/Growth/Quality/Momentum/Volatility)")

    factor_ticker = "AAPL"

    # Value Factors
    try:
        val = ValueFactors(factor_ticker)
        value_results = {
            "price_to_book": val.price_to_book(),
            "book_to_market": val.book_to_market(),
            "trailing_pe": val.trailing_pe(),
            "forward_pe": val.forward_pe(),
            "earnings_yield": val.earnings_yield(),
            "price_to_sales": val.price_to_sales(),
            "price_to_cashflow": val.price_to_cashflow(),
            "free_cashflow_yield": val.free_cashflow_yield(),
            "ev_to_ebitda": val.ev_to_ebitda(),
            "ev_to_ebit": val.ev_to_ebit(),
            "dividend_yield": val.dividend_yield(),
            "peg_ratio": val.peg_ratio(),
        }
        print("ValueFactors:", {k: (None if v is None else round(v, 6)) for k, v in value_results.items()})
    except Exception as e:
        print(f"[WARN] ValueFactors failed: {e}")

    # Growth Factors
    try:
        gr = GrowthFactors(factor_ticker)
        growth_results = {
            "eps_growth_rate": gr.eps_growth_rate(),
            "eps_cagr": gr.eps_cagr(),
            "revenue_growth_rate": gr.revenue_growth_rate(),
            "sales_trend_growth_factor": gr.sales_trend_growth_factor(),
            "fcf_growth_rate": gr.fcf_growth_rate(),
            "peg_ratio": gr.peg_ratio(),
            "roe_growth_rate": gr.roe_growth_rate(),
            "roic_growth_rate": gr.roic_growth_rate(),
            "book_value_growth_rate": gr.book_value_growth_rate(),
            "ocf_growth_rate": gr.ocf_growth_rate(),
        }
        print("GrowthFactors:", {k: (None if (v is None or (isinstance(v, float) and pd.isna(v))) else round(float(v), 6)) for k, v in growth_results.items()})
    except Exception as e:
        print(f"[WARN] GrowthFactors failed: {e}")

    # Quality Factors
    try:
        qf = QualityFactors(factor_ticker)
        quality_results = {
            "return_on_equity": qf.return_on_equity(),
            "return_on_assets": qf.return_on_assets(),
            "roic": qf.roic(),
            "gross_profitability": qf.gross_profitability(),
            "gross_margin": qf.gross_margin(),
            "net_margin": qf.net_margin(),
            "fcf_margin": qf.fcf_margin(),
            "debt_to_equity": qf.debt_to_equity(),
            "net_debt_to_ebitda": qf.net_debt_to_ebitda(),
            "interest_coverage": qf.interest_coverage(),
            "quick_ratio": qf.quick_ratio(),
            "altman_z_score": qf.altman_z_score(),
            "accruals_ratio": qf.accruals_ratio(),
            "earnings_stability": qf.earnings_stability(),
            "eps_revision_3m": qf.eps_revision_3m(),
            "dividend_payout": qf.dividend_payout(),
            "asset_turnover": qf.asset_turnover(),
            "cash_conversion_ratio": qf.cash_conversion_ratio(),
            "cash_flow_to_debt_ratio": qf.cash_flow_to_debt_ratio(),
            "conservative_financing": qf.conservative_financing(),
            "return_on_capital_employed": qf.return_on_capital_employed(),
        }
        print("QualityFactors:", {k: (v if isinstance(v, bool) else (None if v is None else round(float(v), 6))) for k, v in quality_results.items()})
    except Exception as e:
        print(f"[WARN] QualityFactors failed: {e}")

    # Momentum Factors
    try:
        # Prices/volume for the factor ticker
        pf = ds.get_price_data(factor_ticker, start, end).frame
        price_series = pf["close"].astype(float)
        vol_series = pf["volume"].astype(float) if "volume" in pf.columns else None
        # No market/sector series (AAPL only)
        mom = MomentumFactors(price_series, vol_series, None, None)
        macd_val, macd_sig = mom.macd()
        momentum_results = {
            "one_month_return": mom.one_month_return(),
            "three_month_return": mom.three_month_return(),
            "six_month_return": mom.six_month_return(),
            "twelve_month_return_ex1m": mom.twelve_month_return_ex1m(),
            "pct_from_52w_high": mom.pct_from_52w_high(),
            "sma_ratio": mom.sma_ratio(),
            "sma_50": mom.sma_50(),
            "sma_200": mom.sma_200(),
            "macd_value": macd_val,
            "macd_signal": macd_sig,
            "rsi": mom.rsi(),
            "idiosyncratic_momentum": None,
            "sector_idiosyncratic_momentum": None,
            "volume_adjusted_momentum": mom.volume_adjusted_momentum(),
        }
        print("MomentumFactors:", {k: (None if (v is None or (isinstance(v, float) and pd.isna(v))) else round(float(v), 6)) for k, v in momentum_results.items()})
    except Exception as e:
        print(f"[WARN] MomentumFactors failed: {e}")

    # Volatility Factors
    try:
        volf = VolatilityFactors(price_series, None)
        vol_results = {
            "realized_vol_30d": volf.realized_vol_30d(),
            "realized_vol_90d": volf.realized_vol_90d(),
            "annualized_volatility": volf.annualized_volatility(252),
            "daily_return_volatility": volf.daily_return_volatility(),
            "beta_1yr": volf.beta_1yr(),
            "idiosyncratic_vol": volf.idiosyncratic_vol(),
            "downside_dev_30d": volf.downside_dev_30d(),
            "max_drawdown_1yr": volf.max_drawdown_1yr(),
            "atr_price_ratio": volf.atr_price_ratio(),
            "variance_ratio_3m_12m": volf.variance_ratio_3m_12m(),
            "skewness": volf.skewness(),
            "kurtosis": volf.kurtosis(),
            "garch_forecast": volf.garch_forecast(),
        }
        print("VolatilityFactors:", {k: (None if (v is None or (isinstance(v, float) and pd.isna(v))) else round(float(v), 6)) for k, v in vol_results.items()})
    except Exception as e:
        print(f"[WARN] VolatilityFactors failed: {e}")


if __name__ == "__main__":
    run_all()


