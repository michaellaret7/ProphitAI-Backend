"""Data loaders for the hourly multi-alpha strategy."""

from __future__ import annotations

import time

import pandas as pd

from prophitai_algo_trading import panel_from_per_ticker
from prophitai_data.db.models.market import Ticker
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers
from prophitai_data.session.decorators import with_session

from config import Config


# ================================
# --> Helper funcs
# ================================

def _clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()

    return out[~out.index.duplicated(keep="last")]


def _fetch_benchmark_close(cfg: Config) -> pd.Series:
    bulk = fetch_bulk_ohlcv_data_for_tickers(
        [cfg.benchmark_ticker],
        cfg.start,
        cfg.end,
        cfg.frequency,
    )
    df = bulk.get(cfg.benchmark_ticker)

    if df is None or df.empty:
        return pd.Series(dtype=float)

    return _clean_ohlcv(df)["close"]


# ================================
# --> Loaders
# ================================

@with_session("market")
def load_universe(cfg: Config, session=None) -> list[str]:
    """Top active non-ETF US stocks by market cap."""
    rows = (
        session.query(Ticker.ticker)
        .filter(Ticker.is_etf.is_(False))
        .filter(Ticker.is_actively_trading.is_(True))
        .filter(Ticker.market_cap.isnot(None))
        .order_by(Ticker.market_cap.desc())
        .limit(cfg.universe_size)
        .all()
    )

    return [row[0] for row in rows]


def load_hourly_data(tickers: list[str], cfg: Config) -> dict[str, pd.DataFrame]:
    """Load hourly OHLCV keyed by ticker."""
    print(f"\nFetching hourly OHLCV for {len(tickers)} tickers {cfg.start} -> {cfg.end}")
    t0 = time.perf_counter()
    bulk = fetch_bulk_ohlcv_data_for_tickers(tickers, cfg.start, cfg.end, cfg.frequency)
    print(f"Fetched in {time.perf_counter() - t0:.1f}s")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        df = bulk.get(ticker)

        if df is None or df.empty:
            continue

        ready[ticker] = _clean_ohlcv(df)

    print(f"Loaded {len(ready)}/{len(tickers)} tickers")

    return ready


def load_hourly_panel(tickers: list[str], cfg: Config):
    """Load hourly OHLCV and convert to a vectorized PricePanel."""
    data = load_hourly_data(tickers, cfg)
    panel = panel_from_per_ticker(data)

    print(
        f"Panel shape: {len(panel.index)} hourly bars x "
        f"{len(panel.tickers)} tickers",
    )

    return panel


def load_benchmark_close(cfg: Config) -> pd.Series:
    """Hourly benchmark close series for analytics metrics."""
    return _fetch_benchmark_close(cfg)


def load_benchmark_returns(cfg: Config) -> pd.Series:
    """Hourly benchmark returns for simple comparison prints."""
    close = _fetch_benchmark_close(cfg)

    if close.empty:
        return close

    return close.pct_change().dropna()
