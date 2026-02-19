"""Convenience helper to build TickerFactors for a market universe.

Used to create the reference population for universe-relative z-scoring
in portfolio factor exposure calculations.
"""

import pandas as pd

from app.repositories.fundamentals.models import FundamentalsResult
from app.core.calc_v2.factors.calc_all import calc_all_factors
from app.core.calc_v2.models.factors import TickerFactors


def build_universe_factors(
    tickers: list[str],
    ohlcv_data: dict[str, pd.DataFrame],
    benchmark_prices: pd.Series,
    fundamentals: dict[str, FundamentalsResult] | None = None,
) -> dict[str, TickerFactors]:
    """Build TickerFactors for each ticker in the universe.

    Args:
        tickers: Universe ticker symbols.
        ohlcv_data: Dict mapping ticker → OHLCV DataFrame.
        benchmark_prices: Benchmark adj_close series (e.g. SPY).
        fundamentals: Optional dict mapping ticker → FundamentalsResult.

    Returns:
        Dict mapping ticker → TickerFactors. Tickers missing from
        ohlcv_data are silently skipped.
    """
    benchmark_returns = benchmark_prices.pct_change().dropna()
    fund_map = fundamentals or {}
    result: dict[str, TickerFactors] = {}

    for ticker in tickers:
        if ticker not in ohlcv_data:
            continue

        ohlcv = ohlcv_data[ticker]
        adj_close = ohlcv['adj_close']
        daily_returns = adj_close.pct_change().dropna()

        result[ticker] = calc_all_factors(
            adj_close=adj_close,
            daily_returns=daily_returns,
            benchmark_returns=benchmark_returns,
            fundamentals=fund_map.get(ticker),
        )

    return result
