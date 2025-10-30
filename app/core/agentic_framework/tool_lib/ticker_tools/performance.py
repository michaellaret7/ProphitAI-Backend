import yaml
from datetime import datetime, timedelta, timezone
import json
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from app.core.calculations.core.data_service import DataService
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import (
    DEFAULT_TRADING_DAYS,
    DEFAULT_RF_ANNUAL,
    DEFAULT_CONFIDENCE,
    DEFAULT_LOOKBACK_MEDIUM,
)
from app.utils.decorators.price_data import with_bulk_price_data
from app.utils.simulation_utils import get_end_date, filter_series_by_date
from app.utils.decorators.tool_validation import validate_ticker_arg, log_simulation_data_range

@validate_ticker_arg()
@with_bulk_price_data(lookback_days=DEFAULT_LOOKBACK_MEDIUM, include_dividends=True)
@log_simulation_data_range()
def get_ticker_performance_and_risk(
    ticker: str,
    *,
    price_data: dict[str, pd.Series] | None = None,
    _simulation_date: Optional[datetime] = None,
) -> str:
    """Performance and risk metrics over a fixed 2-year window for a single ticker.

    Args:
        ticker: Stock ticker symbol
        price_data: Optional pre-fetched price data (from decorator)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents.
                         If provided, uses this as cutoff date instead of current time.

    - Accepts a single ticker symbol (decorator fetches close series into price_data)
    - Always includes dividends in calculations
    - Always uses SPY as the market benchmark

    Note: Uses @validate_ticker_arg() decorator to validate BEFORE @with_bulk_price_data fetches data.
    """
    # Fixed parameters (2 years of trading days - Bloomberg standard for beta)
    market_ticker = "SPY"
    include_dividends = True
    ds = DataService()
    end_dt = get_end_date(_simulation_date)
    # Convert trading days to calendar days for date range: 504 trading days * (365/252) ≈ 730 calendar days
    start_dt = end_dt - timedelta(days=365)

    def _adjust_for_splits(prices: pd.Series) -> pd.Series:
        """Return split-adjusted close series inferred from large price jumps.

        Heuristic: if day-over-day ratio < 0.7, treat as forward split with factor
        nearest to {2,3,4,5,10}; if ratio > 1.4, treat as reverse split similarly.
        Earlier history is scaled so the series is continuous on the latest scale.
        """
        if prices is None or prices.empty:
            return prices
        s = prices.astype(float).copy()
        ratio = (s / s.shift(1)).dropna()
        factors = []  # (loc, factor)
        candidate_set = np.array([2, 3, 4, 5, 10], dtype=float)
        for idx, r in ratio.items():
            try:
                if r < 0.7 and r > 0:  # forward split
                    f = float(candidate_set[np.argmin(np.abs((1.0 / r) - candidate_set))])
                    if abs((1.0 / r) - f) < 0.15:  # snap tolerance
                        factors.append((idx, f))
                elif r > 1.4:  # reverse split
                    f = float(candidate_set[np.argmin(np.abs(r - candidate_set))])
                    if abs(r - f) < 0.15:
                        factors.append((idx, 1.0 / f))  # reverse split → scale down later history
            except Exception:
                continue
        if not factors:
            return s
        # Build cumulative adjustment factor (latest scale)
        adj = pd.Series(1.0, index=s.index, dtype=float)
        for when, f in factors:
            # multiply all prior dates strictly before 'when' by f (forward split)
            adj.loc[adj.index < when] *= f
        return s / adj

    # Market series for market-dependent metrics
    try:
        mkt_df = ds.get_price_data(market_ticker, start_dt, end_dt).frame
        mkt_close = mkt_df["close"].astype(float).dropna()
        mkt_close = filter_series_by_date(mkt_close, _simulation_date)
        rm = ReturnsCalculator.daily_price_returns(mkt_close)
    except Exception:
        rm = None

    # Normalize ticker (validation handled by @validate_ticker_arg decorator)
    tkr = ticker.strip().upper()

    def _round_map(d: Dict[str, Any], ndigits: int = 4) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in d.items():
            try:
                if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                    out[k] = np.nan
                elif isinstance(v, (int, float, np.floating)):
                    out[k] = float(round(float(v), ndigits))
                else:
                    out[k] = v
            except Exception:
                out[k] = v
        return out

    try:
        close = price_data.get(tkr) if price_data else None
        if close is None or close.empty:
            # Fallback fetch if decorator missed it
            px_df = ds.get_price_data(tkr, start_dt, end_dt).frame
            close = px_df["close"].astype(float).dropna()

        # Filter by simulation date if provided
        close = filter_series_by_date(close, _simulation_date)

        # Heuristic split-adjust for price-only return comparability (TradingView often uses adjusted)
        if close is not None and not close.empty:
            close = _adjust_for_splits(close)
        if close is None or close.empty:
            return yaml.dump({"success": False, "error": f"no price data for {tkr}"}, default_flow_style=False)

        if include_dividends:
            try:
                divs = ds.get_dividends(tkr, start_dt, end_dt).series
                divs = filter_series_by_date(divs, _simulation_date)
                divs = divs.reindex(close.index).fillna(0.0)
            except Exception:
                divs = None
            r = ReturnsCalculator.total_returns(close, divs)
        else:
            r = ReturnsCalculator.daily_price_returns(close)
        if r.empty:
            return yaml.dump({"success": False, "error": f"failed to compute returns for {tkr}"}, default_flow_style=False)

        # Risk
        ann_vol = RiskCalculator.annualized_volatility(r)
        risk: Dict[str, Any] = {
            "annualized_volatility": float(ann_vol) if np.isfinite(ann_vol) else np.nan,
            "max_drawdown": float(RiskCalculator.max_drawdown(close)),
            "ulcer_index_price": float(RiskCalculator.ulcer_index(close)),
            "historical_var_1d": float(RiskCalculator.historical_var(r, confidence=DEFAULT_CONFIDENCE)),
            "expected_shortfall_1d": float(RiskCalculator.expected_shortfall(r, confidence=DEFAULT_CONFIDENCE)),
            "parametric_var_1d": float(RiskCalculator.parametric_var(ann_vol, confidence=DEFAULT_CONFIDENCE)),
            "parametric_cvar_1d": float(RiskCalculator.parametric_cvar(ann_vol, confidence=DEFAULT_CONFIDENCE)),
        }
        if rm is not None and not rm.empty:
            beta = RiskCalculator.beta(r, rm)
            up_b, down_b = RiskCalculator.up_down_beta(r, rm)
            risk.update(
                {
                    "beta": float(beta) if np.isfinite(beta) else np.nan,
                    "up_beta": float(up_b) if np.isfinite(up_b) else np.nan,
                    "down_beta": float(down_b) if np.isfinite(down_b) else np.nan,
                }
            )
        else:
            risk.update({"beta": np.nan, "up_beta": np.nan, "down_beta": np.nan})

        # Round risk values to 4 decimals
        risk = _round_map(risk, ndigits=4)

        # Performance
        perf: Dict[str, Any] = {
            "cagr": float(PerformanceCalculator.cagr_from_returns(r)),
            "sharpe": float(PerformanceCalculator.sharpe_ratio(r, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            "sortino": float(PerformanceCalculator.sortino_ratio(r, mar_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            "calmar_1y": float(PerformanceCalculator.calmar_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS, years=1)),
            "omega": float(PerformanceCalculator.omega_ratio_from_annual(r, mar_annual=0.0, periods_per_year=DEFAULT_TRADING_DAYS)),
            "sterling": float(PerformanceCalculator.sterling_ratio_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS)),
            "burke": float(PerformanceCalculator.burke_ratio(r, periods_per_year=DEFAULT_TRADING_DAYS)),
            "martin": float(PerformanceCalculator.martin_ratio(r, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
            "win_rate": float(PerformanceCalculator.win_rate(r)),
            "profit_factor": float(PerformanceCalculator.profit_factor_from_returns(r)),
            "pain_index": float(PerformanceCalculator.pain_index(r)),
            "tail_ratio": float(PerformanceCalculator.tail_ratio(r)),
            "gain_loss_ratio": float(PerformanceCalculator.gain_loss_ratio(r)),
            "ulcer_index_252": float(PerformanceCalculator.ulcer_index(r, window=DEFAULT_TRADING_DAYS, as_percent=False)),
        }
        if rm is not None and not rm.empty:
            perf.update(
                {
                    "treynor": float(PerformanceCalculator.treynor_ratio(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
                    "information_ratio": float(PerformanceCalculator.information_ratio(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)),
                    "alpha_jensen": float(PerformanceCalculator.alpha_jensen(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
                    "tracking_error": float(PerformanceCalculator.tracking_error(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)),
                    "appraisal_ratio": float(PerformanceCalculator.appraisal_ratio(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)),
                }
            )
            up_d, down_d = PerformanceCalculator.capture_ratios(r, rm, periods_per_year=None)
            up_a, down_a = PerformanceCalculator.capture_ratios(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)
            perf.update(
                {
                    "up_capture_daily": float(up_d) if up_d is not None and np.isfinite(up_d) else np.nan,
                    "down_capture_daily": float(down_d) if down_d is not None and np.isfinite(down_d) else np.nan,
                    "up_capture_ann": float(up_a) if up_a is not None and np.isfinite(up_a) else np.nan,
                    "down_capture_ann": float(down_a) if down_a is not None and np.isfinite(down_a) else np.nan,
                }
            )
        else:
            perf.update(
                {
                    "treynor": np.nan,
                    "information_ratio": np.nan,
                    "alpha_jensen": np.nan,
                    "tracking_error": np.nan,
                    "appraisal_ratio": np.nan,
                    "up_capture_daily": np.nan,
                    "down_capture_daily": np.nan,
                    "up_capture_ann": np.nan,
                    "down_capture_ann": np.nan,
                }
            )

        # Round performance values to 4 decimals
        perf = _round_map(perf, ndigits=4)

        # Returns summary using calendar windows (closer to public site definitions)
        def _trailing_price_return(prices: pd.Series, months: int) -> float:
            if prices is None or prices.empty:
                return np.nan
            end_idx = prices.index[-1]
            start_cut = end_idx - pd.DateOffset(months=months)
            window = prices.loc[prices.index >= start_cut]
            if window.empty:
                return np.nan
            first_px = float(window.iloc[0])
            last_px = float(window.iloc[-1])
            if first_px <= 0:
                return np.nan
            return float(last_px / first_px - 1.0)

        price_return_3y = _trailing_price_return(close, months=36)
        pr_1y = _trailing_price_return(close, months=12)
        pr_6m = _trailing_price_return(close, months=6)
        pr_3m = _trailing_price_return(close, months=3)
        # Total return windows (reinvested)
        try:
            divs_full = DataService().get_dividends(tkr, start_dt, end_dt).series
            divs_full = divs_full.reindex(close.index).fillna(0.0)
        except Exception:
            divs_full = None
        # 3-year
        end_idx = close.index[-1]
        start3 = end_idx - pd.DateOffset(months=36)
        c3 = close.loc[close.index >= start3]
        d3 = divs_full.reindex(c3.index) if divs_full is not None else None
        total_return_3y = float(ReturnsCalculator.holding_period_return_total_reinvested(c3, d3)) if not c3.empty else np.nan
        # 1-year
        start1 = end_idx - pd.DateOffset(months=12)
        c1 = close.loc[close.index >= start1]
        d1 = divs_full.reindex(c1.index) if divs_full is not None else None
        total_return_1y = float(ReturnsCalculator.holding_period_return_total_reinvested(c1, d1)) if not c1.empty else np.nan
        # 6 months
        start6 = end_idx - pd.DateOffset(months=6)
        c6 = close.loc[close.index >= start6]
        d6 = divs_full.reindex(c6.index) if divs_full is not None else None
        total_return_6m = float(ReturnsCalculator.holding_period_return_total_reinvested(c6, d6)) if not c6.empty else np.nan
        # 3 months
        start3m = end_idx - pd.DateOffset(months=3)
        c3m = close.loc[close.index >= start3m]
        d3m = divs_full.reindex(c3m.index) if divs_full is not None else None
        total_return_3m = float(ReturnsCalculator.holding_period_return_total_reinvested(c3m, d3m)) if not c3m.empty else np.nan
        returns: Dict[str, Any] = {
            "price_return_3y": price_return_3y,
            "total_return_3y": total_return_3y,
            "total_return_1y": total_return_1y,
            "total_return_6m": total_return_6m,
            "total_return_3m": total_return_3m,
            "price_return_1y": pr_1y,
            "price_return_6m": pr_6m,
            "price_return_3m": pr_3m,
        }
        returns = _round_map(returns, ndigits=4)

        return yaml.dump({
            "success": True,
            "data": {
                "ticker": tkr,
                "market_ticker": market_ticker.upper() if market_ticker else None,
                "num_observations": int(len(r)),
                "risk": risk,
                "performance": perf,
                "returns": returns,
            }
        }, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": f"failed to compute metrics for {tkr}: {e}"}, default_flow_style=False)


# Tool Schema Constants
GET_TICKER_PERFORMANCE_AND_RISK_DESCRIPTION = (
    "Calculate comprehensive performance and risk metrics for a single ticker over 2 years of data (Bloomberg standard). "
    "Returns detailed metrics including risk measures (Sharpe, Sortino, Treynor, Information Ratio, Alpha, "
    "Omega, Sterling, Burke, Martin ratios), performance metrics (capture ratios, win rates, profit factors), "
    "risk measures (pain index, tail ratio, gain/loss ratio, ulcer index, max drawdown), and returns "
    "across multiple timeframes (2Y, 1Y, 6M, 3M). "
    "CRITICAL: You MUST ALWAYS include the ticker parameter. "
    "Example: get_ticker_performance_and_risk(ticker='AAPL')"
)

GET_TICKER_PERFORMANCE_AND_RISK_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "The ticker symbol to analyze. Must be a valid stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL'). "
                "The function will automatically fetch 2 years of price and dividend data for analysis (Bloomberg standard for beta calculation)."
            ),
            "pattern": "^[A-Z]{1,5}$",
            "minLength": 1,
            "maxLength": 5
        },
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_TICKER_PERFORMANCE_AND_RISK_TOOL = {
    "name": "get_ticker_performance_and_risk",
    "description": GET_TICKER_PERFORMANCE_AND_RISK_DESCRIPTION,
    "parameters": GET_TICKER_PERFORMANCE_AND_RISK_PARAMETERS,
    "function": get_ticker_performance_and_risk,
}
