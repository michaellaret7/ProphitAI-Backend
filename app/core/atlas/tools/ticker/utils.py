"""Shared utilities for tools ticker tools."""

from __future__ import annotations

from typing import cast, TYPE_CHECKING

import pandas as pd

from app.core.calc_v2.ticker import Ticker
from app.core.calc_v2.models.factors import TickerFactors
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.cache.data_cache import get_cache
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

if TYPE_CHECKING:
    from app.utils.cache.data_cache import DataCache

SPY = "SPY"


def build_ticker_obj(
    ticker: str,
    years_back: int,
    fundamentals: bool = False,
) -> Ticker:
    """Fetch OHLCV data and construct a Ticker object with benchmark.

    Checks the process-level ticker_factors cache before computing.
    Stores computed factors back into the cache for future callers.

    Args:
        ticker: Uppercase ticker symbol.
        years_back: Number of years of historical data.
        fundamentals: If True, also fetch fundamentals for factor calculations.
    """
    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(years_back * 365).strftime("%Y-%m-%d")

    tickers_to_fetch = [ticker]
    if ticker != SPY:
        tickers_to_fetch.append(SPY)

    data = fetch_bulk_ohlcv_data_for_tickers(tickers_to_fetch, start_date, end_date)

    if ticker not in data or data[ticker].empty:
        raise ValueError(f"No price data found for {ticker}")

    benchmark_prices = cast(pd.Series, data[SPY]["adj_close"]) if ticker != SPY else None

    # Reason: check ticker_factors cache to avoid redundant factor computation
    cache = get_cache()
    cached_factors = _get_cached_factors(cache, ticker, fundamentals)

    fund_result = None
    if fundamentals and cached_factors is None:
        from app.repositories.fundamentals.fetchers import get_bulk_fundamentals
        fund_result = get_bulk_fundamentals([ticker]).get(ticker)

    ticker_obj = Ticker(
        ticker,
        data[ticker],
        benchmark_prices=benchmark_prices,
        fundamentals=fund_result,
        factors=cached_factors,
    )

    if cached_factors is None:
        cache.put_ticker_factors({ticker: ticker_obj.factors})

    return ticker_obj


def _get_cached_factors(
    cache: "DataCache", ticker: str, needs_fundamentals: bool,
) -> TickerFactors | None:
    """Return cached factors if they satisfy the request, else None.

    Treats a cache hit with value=None as a miss when the caller
    needs fundamentals-enriched factors.
    """
    cached, missing = cache.get_ticker_factors([ticker])
    if missing:
        return None

    factors = cached[ticker]

    # Reason: cached factors may be price-only (no fundamentals).
    # If caller needs fundamentals, recompute to get value/quality/growth/size.
    if needs_fundamentals and factors.value is None:
        return None

    return factors
