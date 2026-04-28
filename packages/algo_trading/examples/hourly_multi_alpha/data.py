"""Data helpers for the hourly multi-alpha example."""

from __future__ import annotations

import time

import pandas as pd

from prophitai_algo_trading import panel_from_per_ticker
from prophitai_data.db.models.market import Ticker
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers
from prophitai_data.session.decorators import with_session


UNIVERSE_SIZE = 250
START = "2024-01-01"
END = "2026-01-01"
FREQUENCY = "hourly"
BENCHMARK_TICKER = "SPY"


@with_session("market")
def load_universe(size: int = UNIVERSE_SIZE, session=None) -> list[str]:
    """Top active non-ETF US stocks by market cap."""
    rows = (
        session.query(Ticker.ticker)
        .filter(Ticker.is_etf.is_(False))
        .filter(Ticker.is_actively_trading.is_(True))
        .filter(Ticker.market_cap.isnot(None))
        .order_by(Ticker.market_cap.desc())
        .limit(size)
        .all()
    )

    return [row[0] for row in rows]


def _clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()

    return out[~out.index.duplicated(keep="last")]


def load_hourly_data(
    tickers: list[str],
    start: str = START,
    end: str = END,
) -> dict[str, pd.DataFrame]:
    """Load hourly OHLCV keyed by ticker."""
    print(f"\nFetching hourly OHLCV for {len(tickers)} tickers {start} -> {end}")
    t0 = time.perf_counter()
    bulk = fetch_bulk_ohlcv_data_for_tickers(tickers, start, end, FREQUENCY)
    print(f"Fetched in {time.perf_counter() - t0:.1f}s")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        df = bulk.get(ticker)

        if df is None or df.empty:
            continue

        ready[ticker] = _clean_ohlcv(df)

    print(f"Loaded {len(ready)}/{len(tickers)} tickers")

    return ready


def load_hourly_panel(
    tickers: list[str],
    start: str = START,
    end: str = END,
):
    """Load hourly OHLCV and convert to a vectorized PricePanel."""
    data = load_hourly_data(tickers, start=start, end=end)
    panel = panel_from_per_ticker(data)

    print(
        f"Panel shape: {len(panel.index)} hourly bars x "
        f"{len(panel.tickers)} tickers",
    )

    return panel


def load_benchmark_returns(
    ticker: str = BENCHMARK_TICKER,
    start: str = START,
    end: str = END,
) -> pd.Series:
    """Hourly benchmark returns for simple comparison prints."""
    bulk = fetch_bulk_ohlcv_data_for_tickers([ticker], start, end, FREQUENCY)
    df = bulk.get(ticker)

    if df is None or df.empty:
        return pd.Series(dtype=float)

    return _clean_ohlcv(df)["close"].pct_change().dropna()


def load_benchmark_close(
    ticker: str = BENCHMARK_TICKER,
    start: str = START,
    end: str = END,
) -> pd.Series:
    """Hourly benchmark close series for analytics metrics."""
    bulk = fetch_bulk_ohlcv_data_for_tickers([ticker], start, end, FREQUENCY)
    df = bulk.get(ticker)

    if df is None or df.empty:
        return pd.Series(dtype=float)

    return _clean_ohlcv(df)["close"]
