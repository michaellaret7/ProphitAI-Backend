"""Tests for the DataCache in-memory caching layer.

Validates OHLCV date-range logic, fundamentals/classifications/ticker-factors
roundtrips, clear(), and the get_cache() singleton with auto-clear on date roll.
"""

import pandas as pd
import pytest

from prophitai_data.cache.data_cache import DataCache, get_cache


# ================================
# --> Helper funcs
# ================================

def _make_ohlcv_df(start: str, end: str) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with a DatetimeIndex spanning *start* to *end*."""
    idx = pd.date_range(start=start, end=end, freq="B")
    return pd.DataFrame(
        {"close": range(len(idx))},
        index=idx,
    )


# ================================
# --> Tests
# ================================

class TestOHLCV:
    """OHLCV put/get roundtrip and date-range validation."""

    def test_put_get_roundtrip(self):
        """Stored OHLCV data is returned when the requested range is covered."""
        cache = DataCache()
        df = _make_ohlcv_df("2024-01-02", "2024-03-29")
        cache.put_ohlcv({"AAPL": df})

        cached, missing = cache.get_ohlcv(["AAPL"], "2024-01-15", "2024-03-15")
        assert "AAPL" in cached
        assert missing == []

    def test_date_range_hit(self):
        """Cache hit when the stored range fully covers the request."""
        cache = DataCache()
        cache.put_ohlcv({"MSFT": _make_ohlcv_df("2024-01-02", "2024-06-28")})

        cached, missing = cache.get_ohlcv(["MSFT"], "2024-02-01", "2024-05-01")
        assert "MSFT" in cached
        assert missing == []

    def test_date_range_miss(self):
        """Cache miss when the stored range does NOT cover the request."""
        cache = DataCache()
        # Reason: store only Jan–Feb, then ask for Jan–Jun
        cache.put_ohlcv({"MSFT": _make_ohlcv_df("2024-01-02", "2024-02-28")})

        cached, missing = cache.get_ohlcv(["MSFT"], "2024-01-02", "2024-06-28")
        assert cached == {}
        assert missing == ["MSFT"]

    def test_returns_missing_tickers(self):
        """Tickers not in the cache appear in the missing list."""
        cache = DataCache()
        cache.put_ohlcv({"AAPL": _make_ohlcv_df("2024-01-02", "2024-03-29")})

        cached, missing = cache.get_ohlcv(
            ["AAPL", "GOOG"], "2024-01-15", "2024-03-15",
        )
        assert "AAPL" in cached
        assert missing == ["GOOG"]


class TestFundamentals:
    """Fundamentals put/get roundtrip."""

    def test_roundtrip(self):
        """Stored fundamentals data is returned for cached tickers."""
        cache = DataCache()
        cache.put_fundamentals({"AAPL": {"pe": 28.5}})

        cached, missing = cache.get_fundamentals(["AAPL"])
        assert cached["AAPL"]["pe"] == pytest.approx(28.5)
        assert missing == []

    def test_missing_tickers(self):
        """Uncached tickers appear in the missing list."""
        cache = DataCache()
        cache.put_fundamentals({"AAPL": {"pe": 28.5}})

        cached, missing = cache.get_fundamentals(["AAPL", "TSLA"])
        assert "AAPL" in cached
        assert missing == ["TSLA"]


class TestClassifications:
    """Classifications put/get roundtrip."""

    def test_roundtrip(self):
        """Stored classification dicts are returned correctly."""
        cache = DataCache()
        data = {"AAPL": {"sector": "Technology", "industry": "Hardware", "sub_industry": None}}
        cache.put_classifications(data)

        cached, missing = cache.get_classifications(["AAPL"])
        assert cached["AAPL"]["sector"] == "Technology"
        assert missing == []


class TestTickerFactors:
    """TickerFactors put/get roundtrip."""

    def test_roundtrip(self):
        """Stored ticker factors are returned correctly."""
        cache = DataCache()
        cache.put_ticker_factors({"AAPL": {"beta": 1.2}})

        cached, missing = cache.get_ticker_factors(["AAPL"])
        assert cached["AAPL"]["beta"] == pytest.approx(1.2)
        assert missing == []


class TestClear:
    """clear() empties all internal stores."""

    def test_clear_empties_all(self):
        """After clear(), every store returns empty results."""
        cache = DataCache()
        cache.put_ohlcv({"AAPL": _make_ohlcv_df("2024-01-02", "2024-03-29")})
        cache.put_fundamentals({"AAPL": {"pe": 30}})
        cache.put_classifications({"AAPL": {"sector": "Tech"}})
        cache.put_ticker_factors({"AAPL": {"beta": 1.1}})

        cache.clear()

        _, m1 = cache.get_ohlcv(["AAPL"], "2024-01-02", "2024-03-29")
        _, m2 = cache.get_fundamentals(["AAPL"])
        _, m3 = cache.get_classifications(["AAPL"])
        _, m4 = cache.get_ticker_factors(["AAPL"])

        assert m1 == ["AAPL"]
        assert m2 == ["AAPL"]
        assert m3 == ["AAPL"]
        assert m4 == ["AAPL"]


class TestGetCacheSingleton:
    """get_cache() singleton and date-roll auto-clear behaviour."""

    def test_returns_same_instance(self):
        """get_cache() returns the same DataCache on repeated calls."""
        a = get_cache()
        b = get_cache()
        assert a is b

    def test_auto_clears_on_date_change(self, monkeypatch):
        """get_cache() clears data when the UTC date rolls forward."""
        import prophitai_data.cache.data_cache as dc_mod

        # Reason: seed the singleton with data under today's date
        cache = get_cache()
        cache.put_fundamentals({"SPY": {"pe": 20}})

        # Simulate a date roll
        monkeypatch.setattr(dc_mod, "get_utc_date_str", lambda: "2099-12-31")

        refreshed = get_cache()
        _, missing = refreshed.get_fundamentals(["SPY"])
        assert missing == ["SPY"]
