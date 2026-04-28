r"""Research every alpha in the hourly multi-alpha strategy.

Run from the repository root:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_alpha_research.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PKG_SRC = CURRENT_DIR.parents[1] / "src"
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(PKG_SRC))

from prophitai_algo_trading import AnalyticsConfig, analyze_alphas, print_alpha_research

from data import load_benchmark_close, load_hourly_panel, load_universe
from strategy import (
    COST_PER_TURNOVER,
    INITIAL_CAPITAL,
    build_alphas,
    build_single_alpha_pcm,
)


def main() -> None:
    print("\n=== Hourly multi-alpha research ===")

    tickers = load_universe()
    panel = load_hourly_panel(tickers)
    benchmark = load_benchmark_close()
    alphas = build_alphas()

    print(f"\nResearching {len(alphas)} alphas:")
    for alpha in alphas:
        print(f"  - {alpha.name}")

    config = AnalyticsConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_per_turnover=COST_PER_TURNOVER,
    )

    t0 = time.perf_counter()
    reports, cross = analyze_alphas(
        alphas=alphas,
        panel=panel,
        pcm_factory=build_single_alpha_pcm,
        config=config,
        benchmark=benchmark if not benchmark.empty else None,
    )
    elapsed = time.perf_counter() - t0

    print(f"\nResearch complete in {elapsed:.1f}s")
    print_alpha_research(reports, cross)


if __name__ == "__main__":
    main()
