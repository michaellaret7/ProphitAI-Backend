"""Shared utilities for tools ticker tools."""

from __future__ import annotations

from typing import cast, TYPE_CHECKING

import pandas as pd

from app.core.calculations.ticker import Ticker
from app.core.calculations.models.factors import TickerFactors
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.cache.data_cache import get_cache
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

if TYPE_CHECKING:
    from app.utils.cache.data_cache import DataCache

SPY = "SPY"


# ================================
# --> Helper funcs
# ================================

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


# ================================
# --> Builders
# ================================

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


def build_ticker_objs_bulk(
    tickers: list[str],
    years_back: int,
    fundamentals: bool = False,
) -> dict[str, Ticker]:
    """Fetch OHLCV data and construct Ticker objects for multiple tickers.

    Single bulk fetch for price data + SPY benchmark, batch cache check,
    and optional bulk fundamentals fetch for uncached tickers.

    Args:
        tickers: Uppercase ticker symbols.
        years_back: Number of years of historical data.
        fundamentals: If True, also fetch fundamentals for factor calculations.

    Returns:
        Dict mapping ticker symbol to Ticker object.
        Tickers with no price data are silently omitted.
    """
    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(years_back * 365).strftime("%Y-%m-%d")

    # Reason: deduplicate SPY — it may already be in the ticker list
    fetch_set = list(dict.fromkeys([*tickers, SPY]))
    data = fetch_bulk_ohlcv_data_for_tickers(fetch_set, start_date, end_date)

    spy_prices = cast(pd.Series, data[SPY]["adj_close"]) if SPY in data else None

    cache = get_cache()

    # Reason: batch cache lookup — one call instead of N
    cached_map, cache_missing = cache.get_ticker_factors(tickers)

    # Reason: for fundamentals-enriched factors, also treat price-only cache hits as missing
    if fundamentals:
        needs_fundamentals = [
            t for t in tickers
            if t in cache_missing or (t in cached_map and cached_map[t].value is None)
        ]
    else:
        needs_fundamentals = []

    fund_map: dict = {}
    if fundamentals and needs_fundamentals:
        from app.repositories.fundamentals.fetchers import get_bulk_fundamentals
        fund_map = get_bulk_fundamentals(needs_fundamentals)

    result: dict[str, Ticker] = {}
    new_factors: dict[str, TickerFactors] = {}

    for t in tickers:
        if t not in data or data[t].empty:
            continue

        benchmark = spy_prices if t != SPY else None
        cached_factors = _get_cached_factors(cache, t, fundamentals) if t not in cache_missing else None

        ticker_obj = Ticker(
            t,
            data[t],
            benchmark_prices=benchmark,
            fundamentals=fund_map.get(t),
            factors=cached_factors,
        )

        if cached_factors is None:
            new_factors[t] = ticker_obj.factors

        result[t] = ticker_obj

    if new_factors:
        cache.put_ticker_factors(new_factors)

    return result
