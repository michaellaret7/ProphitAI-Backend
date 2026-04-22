"""Export 15-minute OHLCV bars from ProphitAI's market_data DB to Lean-ready CSVs.

For each ticker in UNIVERSE, writes:
    projects/qc_test/data/alternative/prophitai/bars_15min/<TICKER>.csv

Schema:
    date,time,open,high,low,close,volume

where `date` is YYYY-MM-DD and `time` is HH:MM:SS at the bar's START time.
Times are converted from UTC (storage) to America/New_York (what the
strategy reasons about, matching Lean's default US-equity algo tz).

Usage:
    source .venv/bin/activate
    python projects/qc_test/scripts/export_data.py --start 2024-06-01 --end 2024-12-31
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


ET = "America/New_York"


#     ================================
# --> Helper funcs
#     ================================

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _universe() -> list[str]:
    sys.path.insert(0, str(_project_root() / "intraday_longshort"))
    from universe import UNIVERSE
    return list(UNIVERSE)


def _export_one(ticker: str, bulk: dict, out_dir: Path) -> int:
    if ticker not in bulk or bulk[ticker].empty:
        print(f"  SKIP {ticker}: no data returned")
        return 0

    df = bulk[ticker].copy()

    df.index = pd.to_datetime(df.index, utc=True)

    df.index = df.index.tz_convert(ET).tz_localize(None)

    df = df.sort_index()

    df = df[(df.index.time >= pd.Timestamp("09:30").time()) &
            (df.index.time <= pd.Timestamp("16:00").time())]

    if df.empty:
        print(f"  SKIP {ticker}: no regular-hours bars")
        return 0

    out_path = out_dir / f"{ticker}.csv"

    with out_path.open("w") as f:
        f.write("date,time,open,high,low,close,volume\n")

        for ts, row in df.iterrows():
            f.write(
                f"{ts.strftime('%Y-%m-%d')},{ts.strftime('%H:%M:%S')},"
                f"{row['open']:.4f},{row['high']:.4f},{row['low']:.4f},"
                f"{row['close']:.4f},{int(row['volume'])}\n"
            )

    return len(df)


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-06-01")
    parser.add_argument("--end", default=datetime.now(UTC).strftime("%Y-%m-%d"))
    args = parser.parse_args()

    out_dir = _project_root() / "data" / "alternative" / "prophitai" / "bars_15min"
    out_dir.mkdir(parents=True, exist_ok=True)

    universe = _universe()

    print(f"Fetching 15-min OHLCV for {len(universe)} tickers "
          f"from {args.start} to {args.end}...")

    bulk = fetch_bulk_ohlcv_data_for_tickers(universe, args.start, args.end, "15mins")

    total_rows = 0
    written = 0

    for ticker in universe:
        rows = _export_one(ticker, bulk, out_dir)
        if rows > 0:
            print(f"  OK  {ticker}: {rows} bars")
            total_rows += rows
            written += 1

    print(f"\nExported {written}/{len(universe)} tickers, {total_rows} total bars.")
    print(f"Target dir: {out_dir}")
    print("\nRun a backtest with:")
    print("    cd projects/qc_test && lean backtest intraday_longshort")


if __name__ == "__main__":
    main()
