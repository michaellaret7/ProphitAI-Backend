"""Investable universe, sector pairs, and data loader for the strategy.

150 liquid US names across 11 GICS sectors. Ten curated same-sector
cointegration pairs are listed separately for
``CointegrationPairAlpha`` to trade — these are well-known empirical
pairs (business-model twins with long trading history), not the
output of an automated pair-discovery step.
"""

from __future__ import annotations

import pandas as pd

from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


#     ================================
# --> Universe (150 tickers)
#     ================================

UNIVERSE: list[str] = [
    # Tech (30)
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN",
    "ORCL", "CRM", "ADBE", "NFLX", "TSLA", "AVGO",
    "INTC", "AMD", "QCOM", "IBM", "AMAT", "LRCX",
    "MU", "TXN", "KLAC", "ADI", "PANW", "CSCO",
    "NOW", "ACN", "SNPS", "CDNS", "UBER", "INTU",
    # Finance (20)
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    "BLK", "SCHW", "AIG", "MET", "PRU", "PNC",
    "USB", "TFC", "COF", "AXP", "MMC", "ICE",
    "CME", "SPGI",
    # Healthcare (20)
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    "TMO", "DHR", "ABT", "BMY", "AMGN", "GILD",
    "CVS", "CI", "VRTX", "REGN", "ISRG", "MDT",
    "SYK", "BSX",
    # Consumer Discretionary (15)
    "HD", "LOW", "NKE", "MCD", "SBUX", "TJX",
    "ROST", "ULTA", "YUM", "CMG", "LULU", "DG",
    "DLTR", "MAR", "BKNG",
    # Consumer Staples (14)
    "WMT", "COST", "TGT", "PG", "KO", "PEP",
    "CL", "KMB", "GIS", "K", "MDLZ", "MO",
    "PM", "STZ",
    # Energy (10)
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY",
    "PSX", "VLO", "MPC", "WMB",
    # Industrial (15)
    "CAT", "GE", "BA", "HON", "UPS", "DE",
    "MMM", "EMR", "ITW", "ETN", "FDX", "LMT",
    "RTX", "NOC", "GD",
    # Communication Services (10)
    "T", "VZ", "DIS", "CMCSA", "TMUS", "CHTR",
    "WBD", "TTWO", "EA", "PARA",
    # Materials (8)
    "LIN", "APD", "SHW", "ECL", "FCX", "NEM",
    "DOW", "DD",
    # Utilities (5)
    "NEE", "DUK", "SO", "AEP", "D",
    # REITs (3)
    "AMT", "PLD", "EQIX",
]

assert len(UNIVERSE) == 150, f"expected 150 tickers, got {len(UNIVERSE)}"


#     ================================
# --> Sector pairs for stat arb
#     ================================

SECTOR_PAIRS: list[tuple[str, str]] = [
    ("KO", "PEP"),      # beverages
    ("XOM", "CVX"),     # integrated oil majors
    ("MA", "V"),        # card networks  (added to universe below? check: no — out of scope here)
    ("JPM", "BAC"),     # money-center banks
    ("GS", "MS"),       # investment banks
    ("T", "VZ"),        # telecom
    ("LLY", "PFE"),     # big pharma
    ("HD", "LOW"),      # home improvement
    ("DUK", "SO"),      # regulated utilities
    ("AMAT", "LRCX"),   # semiconductor equipment
]

# Reason: SECTOR_PAIRS may reference tickers outside UNIVERSE (e.g. MA/V
# were in the old 50-ticker list). Filter to pairs where both legs are
# in-universe so the pair alpha doesn't silently drop ambiguous trades.
SECTOR_PAIRS = [(a, b) for a, b in SECTOR_PAIRS if a in UNIVERSE and b in UNIVERSE]


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
