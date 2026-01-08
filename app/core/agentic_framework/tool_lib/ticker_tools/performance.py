from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import (
    DEFAULT_TRADING_DAYS,
    DEFAULT_RF_ANNUAL,
    DEFAULT_CONFIDENCE,
    DEFAULT_LOOKBACK_2Y,
)
from app.utils.decorators.price_data import with_bulk_price_data
from app.utils.simulation_utils import get_end_date, filter_series_by_date
from app.utils.decorators.tool_validation import validate_ticker_arg, log_simulation_data_range

# Metric group definitions for single ticker filtering
SINGLE_TICKER_METRIC_GROUPS = {
    "core": {
        "risk": ["annualized_volatility", "max_drawdown", "beta"],
        "performance": ["cagr", "sharpe", "sortino"],
        "returns": ["total_return_1y", "total_return_3m"]
    },
    "risk_metrics": {
        "risk": ["annualized_volatility", "max_drawdown", "ulcer_index_price", "historical_var_1d", "expected_shortfall_1d", "parametric_var_1d", "parametric_cvar_1d", "beta", "up_beta", "down_beta"]
    },
    "performance_metrics": {
        "performance": ["cagr", "sharpe", "sortino", "calmar_1y", "omega", "sterling", "burke", "martin", "win_rate", "profit_factor", "pain_index", "tail_ratio", "gain_loss_ratio", "ulcer_index_252", "treynor", "information_ratio", "alpha", "tracking_error", "appraisal_ratio", "up_capture_daily", "down_capture_daily", "up_capture_ann", "down_capture_ann"]
    },
    "returns_metrics": {
        "returns": ["price_return_3y", "total_return_3y", "total_return_1y", "total_return_6m", "total_return_3m", "price_return_1y", "price_return_6m", "price_return_3m"]
    },
    "risk_adjusted": {
        "performance": ["sharpe", "sortino", "calmar_1y", "omega", "sterling", "burke", "martin"]
    },
    "benchmark_relative": {
        "risk": ["beta", "up_beta", "down_beta"],
        "performance": ["treynor", "information_ratio", "alpha", "tracking_error", "appraisal_ratio", "up_capture_daily", "down_capture_daily", "up_capture_ann", "down_capture_ann"]
    },
}

@validate_ticker_arg()
@with_bulk_price_data(lookback_days=DEFAULT_LOOKBACK_2Y, include_dividends=True)
@log_simulation_data_range()
def get_ticker_performance_and_risk(
    ticker: str,
    filters: list[str] = ["all"],
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

    # Date strings for repository calls
    start_str = start_dt.strftime('%Y-%m-%d')
    end_str = end_dt.strftime('%Y-%m-%d')

    # Market series for market-dependent metrics
    try:
        mkt_data = fetch_bulk_price_data_for_tickers([market_ticker], start_str, end_str)
        mkt_close = mkt_data.get(market_ticker)
        if mkt_close is not None:
            mkt_close = mkt_close.astype(float).dropna()
            mkt_close = filter_series_by_date(mkt_close, _simulation_date)
            rm = ReturnsCalculator.daily_price_returns(mkt_close)
        else:
            rm = None
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
            fallback_data = fetch_bulk_price_data_for_tickers([tkr], start_str, end_str)
            close = fallback_data.get(tkr)
            if close is not None:
                close = close.astype(float).dropna()

        # Filter by simulation date if provided
        close = filter_series_by_date(close, _simulation_date)

        # Heuristic split-adjust for price-only return comparability (TradingView often uses adjusted)
        if close is not None and not close.empty:
            close = _adjust_for_splits(close)
        if close is None or close.empty:
            return error_response(f"no price data for {tkr}")

        # Reason: adj_close already accounts for dividends, so daily_price_returns gives total returns
        r = ReturnsCalculator.daily_price_returns(close)
        if r.empty:
            return error_response(f"failed to compute returns for {tkr}")

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
                    "alpha": float(PerformanceCalculator.alpha(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)),
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
                    "alpha": np.nan,
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

        # Returns summary using calendar windows
        # Reason: adj_close accounts for dividends, so price returns on adj_close = total returns
        def _trailing_return(prices: pd.Series, months: int) -> float:
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

        # Calculate returns for various periods (adj_close gives total returns)
        return_3y = _trailing_return(close, months=36)
        return_1y = _trailing_return(close, months=12)
        return_6m = _trailing_return(close, months=6)
        return_3m = _trailing_return(close, months=3)

        returns: Dict[str, Any] = {
            "price_return_3y": return_3y,
            "total_return_3y": return_3y,  # Same as price return since adj_close includes dividends
            "total_return_1y": return_1y,
            "total_return_6m": return_6m,
            "total_return_3m": return_3m,
            "price_return_1y": return_1y,
            "price_return_6m": return_6m,
            "price_return_3m": return_3m,
        }
        returns = _round_map(returns, ndigits=4)

        # Build complete data structure
        all_data = {
            "ticker": tkr,
            "market_ticker": market_ticker.upper() if market_ticker else None,
            "num_observations": int(len(r)),
            "risk": risk,
            "performance": perf,
            "returns": returns,
        }

        # Apply filters
        if "all" in filters or not filters:
            # Return everything (backward compatible)
            filtered_data = all_data
        else:
            # Build filtered data based on requested groups
            filtered_data = {
                "ticker": tkr,
                "market_ticker": market_ticker.upper() if market_ticker else None,
                "num_observations": int(len(r)),
            }

            # Collect requested metrics from each section
            for filter_name in filters:
                if filter_name in SINGLE_TICKER_METRIC_GROUPS:
                    group_def = SINGLE_TICKER_METRIC_GROUPS[filter_name]

                    # Add metrics from each section (risk, performance, returns)
                    for section, metrics in group_def.items():
                        if section not in filtered_data:
                            filtered_data[section] = {}
                        for metric in metrics:
                            if section == "risk" and metric in risk:
                                filtered_data[section][metric] = risk[metric]
                            elif section == "performance" and metric in perf:
                                filtered_data[section][metric] = perf[metric]
                            elif section == "returns" and metric in returns:
                                filtered_data[section][metric] = returns[metric]
                else:
                    # Invalid filter name - return error
                    valid_filters = list(SINGLE_TICKER_METRIC_GROUPS.keys()) + ["all"]
                    return error_response(f"Invalid filter '{filter_name}'. Valid filters: {valid_filters}")

        return success_response(filtered_data)
    except Exception as e:
        return error_response(f"failed to compute metrics for {tkr}: {e}")


# Tool Schema Constants
GET_TICKER_PERFORMANCE_AND_RISK_DESCRIPTION = (
    "Calculate performance and risk metrics for a single ticker with optional filtering for token efficiency. "
    "Returns 41 total metrics across 3 categories (risk, performance, returns) with 6 filter groups available. "
    "\n\n**TOKEN EFFICIENCY - Use Filters to Reduce Response Size:**"
    "\n  Full response (filters=['all']): ~400 tokens (41 metrics across 3 sections)"
    "\n  Filtered response (filters=['core']): ~100 tokens (8 metrics, 75% reduction)"
    "\n  Risk only (filters=['risk_metrics']): ~120 tokens (10 metrics, 70% reduction)"
    "\n\n**Common Filter Patterns:**"
    "\n  • Quick check: ['core']"
    "\n  • Risk analysis: ['risk_metrics', 'risk_adjusted']"
    "\n  • Benchmark comparison: ['core', 'benchmark_relative']"
    "\n  • Full analysis: ['all'] (default)"
    "\n\n**Critical Requirements:**"
    "\n  • You MUST include the ticker parameter"
    "\n  • Use filters to request only needed metrics"
    "\n  • Default lookback: 2 years (504 days), benchmark: SPY"
    "\n\n**Examples:**"
    "\n  get_ticker_performance_and_risk(ticker='AAPL', filters=['core'])"
    "\n  get_ticker_performance_and_risk(ticker='AAPL', filters=['risk_metrics', 'returns_metrics'])"
    "\n  get_ticker_performance_and_risk(ticker='AAPL', filters=['all'])"
)

GET_TICKER_PERFORMANCE_AND_RISK_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "The ticker symbol to analyze (e.g., 'AAPL', 'MSFT', 'GOOGL'). "
                "Automatically fetches 2 years of data (Bloomberg standard for beta)."
            ),
            "pattern": "^[A-Z]{1,5}$",
            "minLength": 1,
            "maxLength": 5
        },
        "filters": {
            "type": "array",
            "description": (
                "Filter which metric groups to return. Reduces token usage by 60-80%. "
                "\n\n**Available Metric Groups:**"
                "\n  • 'core' (8 metrics): Key metrics from risk, performance, and returns"
                "\n    - risk: annualized_volatility, max_drawdown, beta"
                "\n    - performance: cagr, sharpe, sortino"
                "\n    - returns: total_return_1y, total_return_3m"
                "\n  • 'risk_metrics' (10 metrics): All risk measures (volatility, VaR, beta, drawdown)"
                "\n  • 'performance_metrics' (23 metrics): All performance ratios (sharpe, sortino, omega, etc.)"
                "\n  • 'returns_metrics' (8 metrics): Returns across timeframes (3M, 6M, 1Y, 3Y)"
                "\n  • 'risk_adjusted' (7 metrics): Risk-adjusted performance (sharpe, sortino, calmar, omega, sterling, burke, martin)"
                "\n  • 'benchmark_relative' (12 metrics): Benchmark comparison (beta, alpha, treynor, capture ratios)"
                "\n  • 'all': Return all 41 metrics (default)"
                "\n\n**Examples:**"
                "\n  filters=['core']  # Essential metrics only"
                "\n  filters=['risk_metrics', 'returns_metrics']  # Risk and returns analysis"
                "\n  filters=['all']  # Everything"
            ),
            "items": {
                "type": "string",
                "enum": ["all", "core", "risk_metrics", "performance_metrics", "returns_metrics", "risk_adjusted", "benchmark_relative"]
            },
            "default": ["all"]
        }
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


if __name__ == "__main__":
    print(get_ticker_performance_and_risk(ticker='AAPL', filters=['returns_metrics']))