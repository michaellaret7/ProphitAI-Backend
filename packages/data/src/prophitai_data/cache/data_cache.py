"""Process-level data cache for OHLCV, fundamentals, classifications, and
ticker factors.

A module-level singleton persists across all agent runs within the same
process. The cache auto-clears once per day when the UTC date changes,
ensuring stale price data is never served after the EOD job writes new rows.

Usage:
    from prophitai_data.cache.data_cache import get_cache
    cache = get_cache()            # always returns the singleton
    cached, missing = cache.get_ohlcv(tickers, start, end)
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import pandas as pd

from prophitai_shared import get_utc_date_str

logger = logging.getLogger(__name__)


class DataCache:
    """In-memory cache shared across all agent runs in a single process.

    Thread-safe via a Lock guarding all get/put/clear operations.
    Agent tools run in ThreadPoolExecutor — concurrent dict.update() and
    iteration on the same dict can raise RuntimeError without locking.

    Stores:
        ohlcv: ticker -> OHLCV DataFrame (with DatetimeIndex)
        fundamentals: ticker -> FundamentalsResult
        classifications: ticker -> {sector, industry, sub_industry}
        ticker_factors: ticker -> TickerFactors
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.ohlcv: dict[str, pd.DataFrame] = {}
        self.fundamentals: dict[str, Any] = {}
        self.classifications: dict[str, dict[str, str | None]] = {}
        self.ticker_factors: dict[str, Any] = {}
        self._cache_date: str = get_utc_date_str()

    # ================================
    # --> Helper funcs
    # ================================

    def _get_by_tickers(self, store: dict[str, Any], tickers: list[str]) -> tuple[dict[str, Any], list[str]]:
        """Generic ticker lookup under lock: returns (cached_hits, missing_tickers)."""
        cached: dict[str, Any] = {}
        missing: list[str] = []
        for t in tickers:
            if t in store:
                cached[t] = store[t]
            else:
                missing.append(t)
        return cached, missing

    def clear(self) -> None:
        """Clear all cached data.

        Does NOT reset _cache_date. The auto-clear in get_cache() handles
        date-boundary resets separately. Call this to invalidate stale data
        within the same calendar day (e.g., after the EOD job writes new rows).
        """
        with self._lock:
            self.ohlcv.clear()
            self.fundamentals.clear()
            self.classifications.clear()
            self.ticker_factors.clear()

    # ================================
    # --> OHLCV methods
    # ================================

    def get_ohlcv(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
    ) -> tuple[dict[str, pd.DataFrame], list[str]]:
        """Look up cached OHLCV data with date range validation.

        A cache hit requires the stored DataFrame to cover [start_date, end_date].
        Returns (cached_hits, missing_tickers).
        """
        req_start = pd.Timestamp(start_date)
        req_end = pd.Timestamp(end_date)
        cached: dict[str, pd.DataFrame] = {}
        missing: list[str] = []

        with self._lock:
            for t in tickers:
                df = self.ohlcv.get(t)
                if df is not None and not df.empty:
                    if df.index[0] <= req_start and df.index[-1] >= req_end:
                        cached[t] = df
                        continue
                missing.append(t)

        return cached, missing

    def put_ohlcv(self, data: dict[str, pd.DataFrame]) -> None:
        """Store OHLCV DataFrames in the cache."""
        with self._lock:
            self.ohlcv.update(data)

    # ================================
    # --> Fundamentals methods
    # ================================

    def get_fundamentals(
        self, tickers: list[str],
    ) -> tuple[dict[str, Any], list[str]]:
        """Look up cached fundamentals. Returns (cached_hits, missing_tickers)."""
        with self._lock:
            return self._get_by_tickers(self.fundamentals, tickers)

    def put_fundamentals(self, data: dict[str, Any]) -> None:
        """Store fundamentals data in the cache."""
        with self._lock:
            self.fundamentals.update(data)

    # ================================
    # --> Classifications methods
    # ================================

    def get_classifications(
        self, tickers: list[str],
    ) -> tuple[dict[str, dict[str, str | None]], list[str]]:
        """Look up cached ticker classifications. Returns (cached_hits, missing_tickers)."""
        with self._lock:
            return self._get_by_tickers(self.classifications, tickers)

    def put_classifications(self, data: dict[str, dict[str, str | None]]) -> None:
        """Store ticker classifications in the cache."""
        with self._lock:
            self.classifications.update(data)

    # ================================
    # --> TickerFactors methods
    # ================================

    def get_ticker_factors(
        self, tickers: list[str],
    ) -> tuple[dict[str, Any], list[str]]:
        """Look up cached ticker factors. Returns (cached_hits, missing_tickers)."""
        with self._lock:
            return self._get_by_tickers(self.ticker_factors, tickers)

    def put_ticker_factors(self, data: dict[str, Any]) -> None:
        """Store computed ticker factors in the cache."""
        with self._lock:
            self.ticker_factors.update(data)


# Reason: module-level singleton — shared across all agent runs in the process.
_cache = DataCache()
_date_roll_lock = threading.Lock()


def get_cache() -> DataCache:
    """Return the process-level data cache, auto-clearing on date change."""
    today = get_utc_date_str()
    if _cache._cache_date != today:
        with _date_roll_lock:
            # Reason: double-check after acquiring lock to avoid redundant clears
            if _cache._cache_date != today:
                _cache.clear()
                _cache._cache_date = today
    return _cache
