"""Portfolio correlation analysis tool.

Provides a tool for analyzing pairwise correlations across portfolio holdings,
surfacing the most and least correlated pairs alongside rolling trend data.
"""

import numpy as np
import pandas as pd
from typing import Annotated

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools_v2.portfolio.utils import build_portfolio_obj


# ================================
# --> Helper funcs
# ================================

def _extract_top_bottom_pairs(
    corr_matrix: pd.DataFrame,
    n: int,
) -> tuple[list[dict], list[dict]]:
    """Extract the top-N highest and lowest correlated pairs from a correlation matrix.

    Args:
        corr_matrix: N×N symmetric correlation DataFrame (tickers as index/columns).
        n: Number of pairs to return for each direction.

    Returns:
        (highest_pairs, lowest_pairs) — each a list of {"pair": [A, B], "correlation": float}.
    """
    tickers = corr_matrix.columns.tolist()
    rows, cols = np.triu_indices(len(tickers), k=1)

    pairs = [
        {"pair": [tickers[r], tickers[c]], "correlation": round(float(corr_matrix.iloc[r, c]), 4)}
        for r, c in zip(rows, cols)
    ]

    sorted_desc = sorted(pairs, key=lambda p: p["correlation"], reverse=True)
    highest = sorted_desc[:n]
    lowest = sorted_desc[-n:][::-1]  # Reason: reverse so lowest correlation is first

    return highest, lowest


def _summarize_rolling_trend(rolling_corr: pd.Series) -> dict:
    """Summarize the rolling average correlation into a trend snapshot.

    Args:
        rolling_corr: pd.Series of rolling average pairwise correlation (DatetimeIndex).

    Returns:
        Dict with current, one_month_ago, direction, and last_month time series.
    """
    if rolling_corr.empty:
        return {
            "current": None,
            "one_month_ago": None,
            "direction": "stable",
            "last_month": [],
        }

    last_month = rolling_corr.iloc[-21:] if len(rolling_corr) >= 21 else rolling_corr

    current = round(float(rolling_corr.iloc[-1]), 4)
    one_month_ago = round(float(last_month.iloc[0]), 4)

    delta = current - one_month_ago
    if delta > 0.02:
        direction = "rising"
    elif delta < -0.02:
        direction = "falling"
    else:
        direction = "stable"

    return {
        "current": current,
        "one_month_ago": one_month_ago,
        "direction": direction,
        "last_month": [
            {"date": str(idx)[:10], "value": round(float(val), 4)}
            for idx, val in last_month.items()
        ],
    }


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_correlation")
def portfolio_correlation(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
    top_n: Annotated[int, Param(min_val=1, max_val=20)] = 5,
) -> str:
    """Analyze pairwise correlations across portfolio holdings.

Returns average pairwise correlation, diversification ratio, the most and least
correlated pairs, and a rolling correlation trend to detect regime changes.

**WHEN TO USE:**
- Evaluating portfolio diversification quality
- Identifying pairs of holdings that move together (high correlation)
- Finding diversifiers (low correlation pairs)
- Detecting correlation regime changes (rising correlation = deteriorating diversification)

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Weights do not need to sum to 1.0
- Requires at least 2 tickers to compute correlations
- Rolling correlation uses a 60-day window

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        years_back: Number of years of historical data to analyze
        top_n: Number of highest/lowest correlated pairs to surface

    Returns:
        YAML-formatted correlation analysis:
        - correlation_metrics: avg_pairwise_correlation, diversification_ratio
        - highest_correlated_pairs: top N most correlated pairs
        - lowest_correlated_pairs: top N least correlated pairs
        - rolling_correlation_trend: current value, one_month_ago, direction, last_month series

    Interpretation Guide:
        avg_pairwise_correlation: Mean of all off-diagonal correlations.
            <0.3 well-diversified, 0.3-0.6 moderate, >0.6 concentrated.
        diversification_ratio: Effective N / Actual N via eigenvalue entropy.
            1.0 = perfectly uncorrelated, 1/N = perfectly correlated.
        highest_correlated_pairs: Pairs most exposed to the same risk factors.
            >0.8 essentially the same bet, 0.6-0.8 significant overlap.
        lowest_correlated_pairs: Best diversifiers in the portfolio.
            <0.2 strong diversification, negative = hedging benefit.
        rolling_correlation_trend.direction: "rising" (>+0.02 delta) means
            diversification is deteriorating; "falling" means improving.

    Examples:
        portfolio_correlation(tickers=["AAPL", "MSFT", "GOOGL"], weights=[0.40, 0.35, 0.25])
        portfolio_correlation(tickers=["AAPL", "JNJ", "XOM", "TLT"], weights=[0.25, 0.25, 0.25, 0.25], top_n=3)

    Raises:
        ValueError: If tickers and weights have different lengths or no price data found
    """
    try:
        if len(tickers) != len(weights):
            return error_response(
                f"tickers ({len(tickers)}) and weights ({len(weights)}) must have the same length"
            )

        if len(tickers) < 2:
            return error_response("At least 2 tickers are required for correlation analysis")

        portfolio = build_portfolio_obj(tickers, weights, years_back)

        # Reason: cap top_n to actual number of unique pairs
        n_pairs = len(tickers) * (len(tickers) - 1) // 2
        effective_top_n = min(top_n, n_pairs)

        highest, lowest = _extract_top_bottom_pairs(portfolio.corr_matrix, effective_top_n)
        trend = _summarize_rolling_trend(portfolio.rolling_avg_correlation)

        return success_response({
            "tickers": portfolio.tickers,
            "years_back": years_back,
            "correlation_metrics": portfolio.correlation_metrics.model_dump(),
            "highest_correlated_pairs": highest,
            "lowest_correlated_pairs": lowest,
            "rolling_correlation_trend": trend,
        })

    except Exception as e:
        return error_response(f"Failed to compute portfolio correlation: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_correlation(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        years_back=1,
    ))
