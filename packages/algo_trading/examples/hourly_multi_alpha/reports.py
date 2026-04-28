"""Result printers shared by the hourly multi-alpha run scripts."""

from __future__ import annotations

import numpy as np
import pandas as pd


# ================================
# --> Helper funcs
# ================================

def _print_metrics(metrics: dict) -> None:
    print("\n--- Metrics ---")

    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key:30s} {value:.4f}")
        else:
            print(f"  {key:30s} {value}")


def _benchmark_stats(equity_curve: pd.DataFrame, benchmark: pd.Series) -> dict[str, float]:
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
        "r_squared": correlation ** 2,
        "alpha_annual_pct": alpha_per_bar * 1750.0 * 100.0,
        "n_obs": float(len(aligned)),
    }


# ================================
# --> Printers
# ================================

def print_event_result(result) -> None:
    """Print metrics + trade summary for an event-driven backtest."""
    _print_metrics(result.metrics)

    print(f"\nEquity bars: {len(result.equity_curve)}")
    print(f"Closed trades: {len(result.trades)}")

    if result.trades.empty:
        return

    long_trades = int((result.trades["direction"] == "long").sum())
    short_trades = int((result.trades["direction"] == "short").sum())
    print(f"Trade breakdown: {long_trades} long / {short_trades} short")

    print("\nExit reasons:")
    print(result.trades["exit_reason"].value_counts(dropna=False).to_string())


def print_vector_result(result, benchmark: pd.Series) -> None:
    """Print metrics + benchmark stats for a vectorized backtest."""
    _print_metrics(result.metrics)

    final_equity = float(result.equity_curve["equity"].iloc[-1])
    initial = float(result.equity_curve["equity"].iloc[0])
    print(
        f"\nFinal equity: ${final_equity:,.0f} "
        f"(initial ${initial:,.0f}, multiplier {final_equity / initial:.3f}x)",
    )

    stats = _benchmark_stats(result.equity_curve, benchmark)

    if not stats:
        return

    print("\nBenchmark stats:")
    print(f"  beta:              {stats['beta']:.3f}")
    print(f"  correlation:       {stats['correlation']:.3f}")
    print(f"  r_squared:         {stats['r_squared']:.3f}")
    print(f"  alpha annual pct:  {stats['alpha_annual_pct']:+.2f}")
    print(f"  aligned obs:       {int(stats['n_obs'])}")
