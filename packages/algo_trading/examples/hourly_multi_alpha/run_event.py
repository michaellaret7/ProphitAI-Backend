r"""Run the blended hourly strategy through the event-driven Backtest.

Run from the repository root:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_event.py
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

from config import Config
from data import load_benchmark_close, load_hourly_data, load_universe
from reports import print_event_result
from strategy import build_event_algorithm


def main() -> None:
    print("\n=== Hourly multi-alpha event backtest ===")

    cfg = Config()
    tickers = load_universe(cfg)
    data = load_hourly_data(tickers, cfg)
    benchmark = load_benchmark_close(cfg)
    algo = build_event_algorithm(cfg)

    print(f"\n{len(algo.alphas)} alphas")

    engine = Backtest(
        algo,
        initial_capital=cfg.initial_capital,
        cost_model=CostModel(ptc=cfg.cost_per_turnover, ftc=1.0),
    )

    t0 = time.perf_counter()
    result = engine.run(data, benchmark=benchmark if not benchmark.empty else None)
    elapsed = time.perf_counter() - t0

    print(f"\nBacktest.run total: {elapsed:.1f}s")
    print_event_result(result)


if __name__ == "__main__":
    main()
