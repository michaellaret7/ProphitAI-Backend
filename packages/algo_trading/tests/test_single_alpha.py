"""Single-alpha research test — deep dive on one alpha signal.

Calls ``analyze_alpha`` (the standalone, non-sweep entry point) on a
single alpha and prints the full ``AlphaReport``: identity, signal-
quality scalars, IC decay table, sub-period stability slices, lag
sensitivity, cost-breakeven curve, and backtest metrics.

Cross-alpha projection fields (``cluster_id``, ``passes_fdr``,
``top_correlations``) stay ``None`` — they only populate when running
through ``analyze_alphas`` with N >= 2 alphas. Graduation also stays
unevaluated for the same reason. To see those, switch to the sweep
test (``test_alpha_research.py``).

To test a different alpha:
    1. Add the alpha class to the import block below.
    2. Change ``ALPHA_TO_TEST`` to that class.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \\
        packages/algo_trading/tests/test_single_alpha.py
"""

from __future__ import annotations

import time
from datetime import timedelta

import pandas as pd

from prophitai_algo_trading import (
    AnalyticsConfig,
    analyze_alpha,
    panel_from_per_ticker,
    print_alpha_report,
)
from prophitai_algo_trading.alpha_signals import (
    MomentumAlpha,
    # Add more imports here when swapping ALPHA_TO_TEST.
)
from prophitai_algo_trading.construction import (
    MagnitudeWeightedLongShortPCM,
)
from prophitai_data.db.models.market import Ticker
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers
from prophitai_data.session.decorators import with_session


#     ================================
# --> Pick the alpha to test
#     ================================

ALPHA_TO_TEST = MomentumAlpha


#     ================================
# --> Universe + window
#     ================================

UNIVERSE_SIZE = 500

BENCHMARK_TICKER = "SPY"

START = "2021-01-01"
END = "2025-12-31"


@with_session('market')
def _load_universe(size: int = UNIVERSE_SIZE, session=None) -> list[str]:
    """Top ``size`` non-ETF tickers by market cap from the market_data DB."""
    rows = (
        session.query(Ticker.ticker)
        .filter(Ticker.is_etf.is_(False))
        .filter(Ticker.is_actively_trading.is_(True))
        .filter(Ticker.market_cap.isnot(None))
        .order_by(Ticker.market_cap.desc())
        .limit(size)
        .all()
    )

    return [row[0] for row in rows]


UNIVERSE: list[str] = _load_universe()


#     ================================
# --> Helper funcs
#     ================================

def _load_benchmark() -> pd.Series:
    print(f"\nFetching benchmark ({BENCHMARK_TICKER}) {START} -> {END}")

    bulk = fetch_bulk_ohlcv_data_for_tickers(
        [BENCHMARK_TICKER], START, END, "daily",
    )

    df = bulk.get(BENCHMARK_TICKER)

    if df is None or df.empty:
        print(f"Benchmark {BENCHMARK_TICKER} unavailable — skipping")

        return pd.Series(dtype=float)

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df["close"]


def _load_panel():
    print(f"\nFetching daily OHLCV for {len(UNIVERSE)} tickers {START} -> {END}")

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

    panel = panel_from_per_ticker(ready)

    print(
        f"Panel shape: {len(panel.index)} bars x "
        f"{len(panel.tickers)} tickers",
    )

    return panel


def _build_pcm():
    """Fresh PCM — same config as the sweep test for apples-to-apples."""
    return MagnitudeWeightedLongShortPCM(
        gross_exposure=1.5,
        per_position_cap=0.10,
        quantile=0.20,
        min_abs_score=0.0,
        rebalance_every=timedelta(weeks=1),
    )


#     ================================
# --> Main
#     ================================

def main() -> None:
    alpha = ALPHA_TO_TEST()

    print(f"\n=== Single-alpha research: {alpha.name} ===")

    panel = _load_panel()
    benchmark = _load_benchmark()

    config = AnalyticsConfig(
        initial_capital=1_000_000.0,
        cost_per_turnover=0.0001,
    )

    print(f"\nResearching {alpha.name} ...")

    t0 = time.perf_counter()

    report = analyze_alpha(
        alpha=alpha,
        panel=panel,
        pcm_factory=_build_pcm,
        config=config,
        benchmark=benchmark if not benchmark.empty else None,
    )

    elapsed = time.perf_counter() - t0

    print(f"Research complete in {elapsed * 1000:.1f} ms")

    print_alpha_report(report)


if __name__ == "__main__":
    main()
