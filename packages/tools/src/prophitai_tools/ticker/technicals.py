"""Ticker technical analysis tool.

Provides a tool for retrieving curated technical indicator series
for tickers, organized by category. Supports batched multi-ticker calls.
"""

from typing import Annotated, Literal

import pandas as pd

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_tools.ticker.utils import build_ticker_objs_bulk
from prophitai_calculations.models.technicals import TickerTechnicals


# ================================
# --> Helper funcs
# ================================

# Reason: curated subset per category — drops redundant/niche indicators
CURATED_FIELDS: dict[str, list[str]] = {
    "trend": ["sma_50", "sma_200", "ema_50", "ema_200", "linreg_slope_50"],
    "momentum": ["rsi_14", "adx_14", "macd_line", "macd_signal", "macd_histogram"],
    "volatility": ["atr_14", "yang_zhang_vol_20", "bollinger_pct_b", "bollinger_bandwidth"],
    "volume": ["cmf_20", "mfi_14", "amihud_illiquidity_21"],
    "statistical": ["z_score_50", "autocorrelation_lag_1"],
}


def _extract_series_table(
    technicals: TickerTechnicals,
    category: str,
    days: int,
) -> list[dict]:
    """Build a date-aligned table of the last N days for a category's curated fields."""

    cat_obj = getattr(technicals, category)
    fields = CURATED_FIELDS[category]

    # Reason: collect non-empty series, align on shared index, then tail
    series_map: dict[str, pd.Series] = {}
    for field in fields:
        s = getattr(cat_obj, field)
        if s is not None and not s.empty:
            series_map[field] = s

    if not series_map:
        return []

    df = pd.DataFrame(series_map)
    df = df.tail(days).round(4)
    df.index = df.index.strftime("%Y-%m-%d")

    rows: list[dict] = []
    for date, row in df.iterrows():
        entry: dict = {"date": date}
        entry.update({k: v for k, v in row.items() if pd.notna(v)})
        rows.append(entry)

    return rows


# ================================
# --> Tools
# ================================

@agent_tool(name="ticker_technicals", category="ticker_analytics")
def ticker_technicals(
    tickers: list[str],
    category: Literal["trend", "momentum", "volatility", "volume", "statistical"],
    days: Annotated[int, Param(min_val=1, max_val=30)] = 20,
) -> str:
    """
    Get technical indicator time series for one or more tickers.

    Returns the last N trading days of curated indicators for the chosen category.
    Use this to analyze trends, momentum shifts, volatility regimes, and volume
    patterns over time.

    Available categories and their indicators:
        trend: sma_50, sma_200, ema_50, ema_200, linreg_slope_50
        momentum: rsi_14, adx_14, macd_line, macd_signal, macd_histogram
        volatility: atr_14, yang_zhang_vol_20, bollinger_pct_b, bollinger_bandwidth
        volume: cmf_20, mfi_14, amihud_illiquidity_21
        statistical: z_score_50, autocorrelation_lag_1

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'KO'])
        category: Technical indicator category to retrieve series data for
        days: Number of trailing trading days of data to return

    Returns:
        YAML with current_price and a date-aligned series table for the chosen category.

    Interpretation Guide:
        rsi_14: 0-100 oscillator. >70 overbought, <30 oversold.
        adx_14: Trend strength. >25 strong trend, <20 no trend.
        macd_histogram: >0 bullish momentum, <0 bearish. Watch for zero-line crossovers.
        bollinger_pct_b: 0-1 position within bands. >0.8 near upper, <0.2 near lower.
        bollinger_bandwidth: Band width relative to price. Narrowing = squeeze forming.
        yang_zhang_vol_20: Best single vol estimator. Rising = increasing uncertainty.
        cmf_20: -1 to 1 money flow. >0.05 accumulation, <-0.05 distribution.
        mfi_14: Volume-weighted RSI. >80 overbought, <20 oversold.
        z_score_50: Std devs from 50d mean. |z|>2 = statistically extreme.
        linreg_slope_50: Direction/steepness of 50d linear trend. Positive = uptrend.

    Examples:
        ticker_technicals(tickers=["AAPL", "MSFT"], category="momentum", days=10)
        >>> {"success": True, "data": {"results": {"AAPL": {...}, "MSFT": {...}}, "errors": {}}}

    Raises:
        ValueError: If no tickers have available price data
    """
    tickers = [t.upper().strip() for t in tickers]

    try:
        ticker_objs = build_ticker_objs_bulk(tickers, 1)
    except Exception as e:
        return error_response(f"Failed to fetch price data: {str(e)}")

    results: dict = {}
    errors: dict = {}

    for t in tickers:
        if t not in ticker_objs:
            errors[t] = f"No price data found for {t}"
            continue

        try:
            obj = ticker_objs[t]
            series = _extract_series_table(obj.technicals, category, days)
            results[t] = {
                "current_price": round(float(obj.adj_close.iloc[-1]), 2),
                "category": category,
                "days": days,
                "series": series,
            }
        except Exception as e:
            errors[t] = str(e)

    return success_response({"results": results, "errors": errors})
