r"""Run the blended hourly strategy through VectorBacktest.

Run from the repository root:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_vector_backtest.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PKG_SRC = CURRENT_DIR.parents[1] / "src"
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(PKG_SRC))

from prophitai_algo_trading import VectorBacktest

from data import load_benchmark_returns, load_hourly_panel, load_universe
from strategy import build_vector_algorithm


def benchmark_stats(equity_curve: pd.DataFrame, benchmark: pd.Series) -> dict[str, float]:
    if equity_curve.empty or benchmark.empty:
        return {}

    strategy_returns = equity_curve["equity"].pct_change().dropna()
    aligned = pd.concat(
        [strategy_returns.rename("strategy"), benchmark.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 10:
        return {}

    strategy = aligned["strategy"].to_numpy(dtype=float)
    bench = aligned["benchmark"].to_numpy(dtype=float)
    bench_var = float(np.var(bench, ddof=1))

    if bench_var <= 0.0:
        return {}

    beta = float(np.cov(strategy, bench, ddof=1)[0, 1]) / bench_var
    correlation = float(np.corrcoef(strategy, bench)[0, 1])
    alpha_per_bar = float(strategy.mean() - beta * bench.mean())

    return {
        "beta": beta,
        "correlation": correlation,
        "r_squared": correlation**2,
        "alpha_annual_pct": alpha_per_bar * 1750.0 * 100.0,
        "n_obs": float(len(aligned)),
    }


def print_metrics(result, benchmark: pd.Series) -> None:
    print("\n--- Metrics ---")
    for key, value in result.metrics.items():
        if isinstance(value, float):
            print(f"  {key:30s} {value:.4f}")
        else:
            print(f"  {key:30s} {value}")

    final_equity = float(result.equity_curve["equity"].iloc[-1])
    initial = float(result.equity_curve["equity"].iloc[0])
    print(
        f"\nFinal equity: ${final_equity:,.0f} "
        f"(initial ${initial:,.0f}, multiplier {final_equity / initial:.3f}x)",
    )

    stats = benchmark_stats(result.equity_curve, benchmark)

    if stats:
        print("\nBenchmark stats:")
        print(f"  beta:              {stats['beta']:.3f}")
        print(f"  correlation:       {stats['correlation']:.3f}")
        print(f"  r_squared:         {stats['r_squared']:.3f}")
        print(f"  alpha annual pct:  {stats['alpha_annual_pct']:+.2f}")
        print(f"  aligned obs:       {int(stats['n_obs'])}")


def main() -> None:
    print("\n=== Hourly multi-alpha vector backtest ===")

    tickers = load_universe()
    panel = load_hourly_panel(tickers)
    benchmark = load_benchmark_returns()
    algo = build_vector_algorithm()

    print(f"\n{len(algo.alphas)} alphas: {algo.alpha_names}")

    engine = VectorBacktest(verbose=True)
    t0 = time.perf_counter()
    result = engine.run(algo, panel)
    elapsed = time.perf_counter() - t0

    print(f"\nVectorBacktest.run total: {elapsed:.1f}s")
    print_metrics(result, benchmark)


if __name__ == "__main__":
    main()
