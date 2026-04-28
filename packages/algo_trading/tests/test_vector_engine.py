"""Smoke test — VectorBacktest end-to-end on real price data.

Runs a small multi-alpha L/S strategy through the vectorized engine
and prints timing + headline metrics. No pytest, no mocks — pulls
daily OHLCV from the market_data DB and exercises the full pipeline:

    panel ─▶ alphas (momentum + reversal + breakout + low_vol + trend_vol)
          ─▶ MultiAlphaBlender(inner=MagnitudeWeightedLongShortConstructor)
          ─▶ weights → returns → equity → metrics

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \\
        packages/algo_trading/tests/test_vector_engine.py
"""

from __future__ import annotations

import time
from datetime import timedelta

import pandas as pd

from prophitai_algo_trading import (
    VectorAlgorithm,
    VectorBacktest,
    panel_from_per_ticker,
)
from prophitai_algo_trading.alpha_signals import (
    BreakoutAlpha,
    LowVolAlpha,
    MomentumAlpha,
    ShortTermReversalAlpha,
    TrendVolumeAlpha,
)
from prophitai_algo_trading.construction import (
    MagnitudeWeightedLongShortConstructor,
    MultiAlphaBlender,
)
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


#     ================================
# --> Universe + window
#     ================================

UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN",
    "ORCL", "CRM", "ADBE", "NFLX", "TSLA", "AVGO",
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    "HD", "LOW", "NKE", "MCD", "SBUX",
    "WMT", "COST", "TGT", "PG", "KO", "PEP",
    "XOM", "CVX", "COP", "SLB", "EOG",
    "CAT", "GE", "BA", "HON", "UPS", "DE",
    "T", "VZ", "DIS", "CMCSA",
]

START = "2021-01-01"
END = "2025-12-31"
INITIAL_CAPITAL = 1_000_000.0


#     ================================
# --> Helper funcs
#     ================================

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


def _build_algo() -> VectorAlgorithm:
    pcm = MultiAlphaBlender(
        weights={
            "momentum":  0.50,
            "reversal":  0.20,
            "breakout":  0.10,
            "low_vol":   0.10,
            "trend_vol": 0.10,
        },
        inner=MagnitudeWeightedLongShortConstructor(
            gross_exposure=1.5,
            per_position_cap=0.10,
            quantile=0.20,
            min_abs_score=0.10,
            rebalance_every=timedelta(weeks=1),
        ),
    )

    return VectorAlgorithm(
        alphas=[
            MomentumAlpha(),
            ShortTermReversalAlpha(),
            BreakoutAlpha(),
            LowVolAlpha(),
            TrendVolumeAlpha(),
        ],
        pcm=pcm,
        initial_capital=INITIAL_CAPITAL,
        cost_per_turnover=0.0001,
    )


#     ================================
# --> Main
#     ================================

def main() -> None:
    print("\n=== VectorBacktest smoke test ===")

    panel = _load_panel()
    algo = _build_algo()

    print(f"\n{len(algo.alphas)} alphas: {algo.alpha_names}")

    engine = VectorBacktest(verbose=True)

    t0 = time.perf_counter()
    result = engine.run(algo, panel)
    elapsed = time.perf_counter() - t0

    print(f"\nVectorBacktest.run total: {elapsed * 1000:.1f} ms")

    print("\n--- Metrics ---")
    for key, value in result.metrics.items():
        print(f"  {key:30s} {value}")

    final_equity = float(result.equity_curve["equity"].iloc[-1])
    initial = float(result.equity_curve["equity"].iloc[0])

    print(
        f"\nFinal equity: ${final_equity:,.0f} "
        f"(initial ${initial:,.0f}, multiplier {final_equity / initial:.3f}x)",
    )


if __name__ == "__main__":
    main()
