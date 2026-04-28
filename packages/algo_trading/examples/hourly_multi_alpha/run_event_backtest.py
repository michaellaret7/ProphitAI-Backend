r"""Run the blended hourly strategy through the event-driven Backtest.

Run from the repository root:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_event_backtest.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PKG_SRC = CURRENT_DIR.parents[1] / "src"
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(PKG_SRC))

from prophitai_algo_trading import Backtest, CostModel

from data import load_benchmark_close, load_hourly_data, load_universe
from strategy import INITIAL_CAPITAL, build_event_algorithm


def print_result(result) -> None:
    print("\n--- Metrics ---")
    for key, value in result.metrics.items():
        if isinstance(value, float):
            print(f"  {key:30s} {value:.4f}")
        else:
            print(f"  {key:30s} {value}")

    print(f"\nEquity bars: {len(result.equity_curve)}")
    print(f"Closed trades: {len(result.trades)}")

    if not result.trades.empty:
        long_trades = int((result.trades["direction"] == "long").sum())
        short_trades = int((result.trades["direction"] == "short").sum())
        print(f"Trade breakdown: {long_trades} long / {short_trades} short")
        print("\nExit reasons:")
        print(result.trades["exit_reason"].value_counts(dropna=False).to_string())


def main() -> None:
    print("\n=== Hourly multi-alpha event backtest ===")

    tickers = load_universe()
    data = load_hourly_data(tickers)
    benchmark = load_benchmark_close()
    algo = build_event_algorithm()

    print(f"\n{len(algo.alphas)} alphas")

    engine = Backtest(
        algo,
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(ptc=0.0001, ftc=1.0),
    )

    t0 = time.perf_counter()
    result = engine.run(data, benchmark=benchmark if not benchmark.empty else None)
    elapsed = time.perf_counter() - t0

    print(f"\nBacktest.run total: {elapsed:.1f}s")
    print_result(result)


if __name__ == "__main__":
    main()
