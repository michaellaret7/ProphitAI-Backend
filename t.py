"""Benchmark: process-level DataCache singleton — cross-run cache hits."""

import time
from app.utils.cache.data_cache import get_cache
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.repositories.fundamentals.fetchers import get_bulk_fundamentals
from app.core.calc_v2.portfolio_analytics.group_metrics import fetch_ticker_classifications
from app.core.calc_v2.portfolio_analytics.factor_exposures import get_universe_factors


# ================================
# --> Config
# ================================

PORTFOLIO_A = ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"]
PORTFOLIO_B = ["AAPL", "MSFT", "GOOG", "NVDA", "BAC", "GS", "HD", "CAT", "XOM", "PG"]
# 4 overlapping tickers: AAPL, MSFT, GOOG, NVDA (+ SPY benchmark fetched both times)

START = "2021-02-25"
END = "2026-02-25"


# ================================
# --> Helper funcs
# ================================

def print_cache_state(label: str) -> None:
    """Print current cache contents inline."""
    cache = get_cache()
    print(f"    [cache] {label}:")
    print(f"      ohlcv={sorted(cache.ohlcv.keys())}")
    print(f"      fundamentals={sorted(cache.fundamentals.keys())}")
    print(f"      classifications={sorted(cache.classifications.keys())}")
    print(f"      ticker_factors={sorted(cache.ticker_factors.keys())}")
    print()


def timed_call(label: str, func, *args, **kwargs):
    """Run a function, print timing and cache state after."""
    t0 = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    print(f"  {label:<30s} {elapsed:>8.3f}s")
    print_cache_state(f"after {label}")
    return elapsed, result


def simulate_agent_run(label: str, portfolio: list[str]) -> dict[str, float]:
    """Simulate an agent calling portfolio tools for a single portfolio."""
    timings: dict[str, float] = {}

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    print_cache_state("before run")

    timings["ohlcv"], _ = timed_call(
        "ohlcv", fetch_bulk_ohlcv_data_for_tickers, portfolio + ["SPY"], START, END,
    )
    timings["fundamentals"], _ = timed_call(
        "fundamentals", get_bulk_fundamentals, portfolio,
    )
    timings["classifications"], _ = timed_call(
        "classifications", fetch_ticker_classifications, portfolio,
    )
    timings["universe_factors"], _ = timed_call(
        "universe_factors", get_universe_factors,
    )

    total = sum(timings.values())
    print(f"  {'-' * 45}")
    print(f"  {'TOTAL':<30s} {total:>8.3f}s")

    return timings


if __name__ == "__main__":
    # Ensure cache starts fresh
    get_cache().clear()

    # Run 1 — cold cache (Portfolio A)
    run1 = simulate_agent_run("RUN 1 (cold cache) — Portfolio A", PORTFOLIO_A)

    # Run 2 — warm cache (Portfolio B has 4 overlapping tickers)
    run2 = simulate_agent_run("RUN 2 (warm cache) — Portfolio B", PORTFOLIO_B)

    # Comparison
    run1_total = sum(run1.values())
    run2_total = sum(run2.values())
    saved = run1_total - run2_total
    pct = (saved / run1_total) * 100 if run1_total > 0 else 0

    print(f"\n{'=' * 60}")
    print(f"  CROSS-RUN CACHE COMPARISON")
    print(f"{'=' * 60}")
    print(f"  Run 1 (cold): {run1_total:>8.3f}s")
    print(f"  Run 2 (warm): {run2_total:>8.3f}s")
    print(f"  Time saved:   {saved:>8.3f}s  ({pct:.1f}%)")

    print(f"\n  Run 2 step savings (overlapping tickers):")
    for key in run1:
        diff = run1[key] - run2[key]
        print(f"    {key:<25s}  {run1[key]:.3f}s -> {run2[key]:.3f}s  (saved {diff:.3f}s)")
