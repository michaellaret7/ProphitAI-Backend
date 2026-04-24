"""Investable universe, sector pairs, and data loader for the strategy.

50 liquid US names across 7 sectors. Six curated same-sector
cointegration pairs are listed separately for ``CointegrationPairAlpha``
to trade — these are well-known empirical pairs (business-model twins
with long trading history), not the output of a pair-discovery step.
"""

from __future__ import annotations

import pandas as pd

from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


#     ================================
# --> Universe
#     ================================

UNIVERSE: list[str] = [
    # Tech (12)
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN",
    "ORCL", "CRM", "ADBE", "NFLX", "TSLA", "AVGO",
    # Finance (6)
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    # Healthcare (6)
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    # Consumer (6)
    "WMT", "HD", "NKE", "MCD", "SBUX", "PG",
    # Energy (4)
    "XOM", "CVX", "COP", "SLB",
    # Industrial (5)
    "CAT", "GE", "BA", "HON", "UPS",
    # Communication (3)
    "T", "VZ", "DIS",
    # Payments + staples + defense (8)
    "KO", "PEP", "MA", "V", "AXP", "UNP", "LMT", "RTX",
]

assert len(UNIVERSE) == 50, f"expected 50 tickers, got {len(UNIVERSE)}"


#     ================================
# --> Sector pairs for stat arb
#     ================================

SECTOR_PAIRS: list[tuple[str, str]] = [
    ("KO", "PEP"),      # beverages
    ("XOM", "CVX"),     # integrated oil majors
    ("MA", "V"),        # card networks
    ("JPM", "BAC"),     # money-center banks
    ("GS", "MS"),       # investment banks
    ("T", "VZ"),        # telecom
]


#     ================================
# --> Backtest window + capital
#     ================================

START = "2023-01-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


#     ================================
# --> Data loader
#     ================================

def load_data() -> dict[str, pd.DataFrame]:
    """Fetch daily OHLCV for ``UNIVERSE`` from the market_data DB.

    Tickers with empty data are dropped from the returned dict — the
    backtest engine handles a partial universe gracefully.
    """
    print(f"Fetching daily OHLCV for {len(UNIVERSE)} tickers {START} -> {END} ...")

    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE, START, END, "daily")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in UNIVERSE:
        df = bulk.get(ticker)

        if df is None or df.empty:
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(UNIVERSE)} tickers")

    return ready
