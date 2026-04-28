r"""Run the blended hourly strategy through VectorBacktest.

Run from the repository root:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_vector.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PKG_SRC = CURRENT_DIR.parents[1] / "src"
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(PKG_SRC))

from prophitai_algo_trading import VectorBacktest

from config import Config
from data import load_benchmark_returns, load_hourly_panel, load_universe
from reports import print_vector_result
from strategy import build_vector_algorithm


def main() -> None:
    print("\n=== Hourly multi-alpha vector backtest ===")

    cfg = Config()
    tickers = load_universe(cfg)
    panel = load_hourly_panel(tickers, cfg)
    benchmark = load_benchmark_returns(cfg)
    algo = build_vector_algorithm(cfg)

    print(f"\n{len(algo.alphas)} alphas: {algo.alpha_names}")

    engine = VectorBacktest(verbose=True)

    t0 = time.perf_counter()
    result = engine.run(algo, panel)
    elapsed = time.perf_counter() - t0

    print(f"\nVectorBacktest.run total: {elapsed:.1f}s")
    print_vector_result(result, benchmark)


if __name__ == "__main__":
    main()
