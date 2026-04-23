"""Real-data test for the 5 Phase 1 AlphaModels.

Pulls daily OHLCV from the market_data DB for a 20-ticker universe,
runs each alpha at the final bar, and grades the emitted Insights
against the underlying price data. No pytest — runs as a plain script.

Run:
    /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_alphas.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Reason: add src to path so we import the package without an install.
_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading.alphas import (
    BreakoutAlpha,
    LowVolAlpha,
    MomentumAlpha,
    ShortTermReversalAlpha,
    TrendVolumeAlpha,
)
from prophitai_algo_trading.framework import AlgorithmContext, AlphaModel, Insight
from prophitai_algo_trading.portfolio import Portfolio
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AVGO",
    "JPM", "BAC", "WFC", "GS",
    "JNJ", "UNH", "LLY", "PFE",
    "XOM", "CVX", "COP",
    "WMT",
]

START = "2023-01-01"
END = "2024-12-31"


#     ================================
# --> Helpers
#     ================================

def _load_bars() -> dict[str, pd.DataFrame]:
    print(f"Fetching daily OHLCV for {len(UNIVERSE)} tickers {START} -> {END} ...")

    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE, START, END, "daily")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in UNIVERSE:
        df = bulk.get(ticker)

        if df is None or df.empty:
            print(f"  SKIP {ticker}: no data")
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(UNIVERSE)} tickers")

    return ready


def _build_context(
    data: dict[str, pd.DataFrame], asof: datetime,
) -> AlgorithmContext:
    """Build an AlgorithmContext with ``data`` sliced up to ``asof``."""
    sliced: dict[str, pd.DataFrame] = {}

    for ticker, df in data.items():
        upto = df.loc[df.index <= pd.Timestamp(asof)]

        if not upto.empty:
            sliced[ticker] = upto

    portfolio = Portfolio(initial_capital=1_000_000.0)

    return AlgorithmContext(
        timestamp=asof,
        portfolio=portfolio,
        data=sliced,
        warmup=False,
    )


def _grade(insights: list[Insight], alpha_name: str) -> None:
    """Print a one-screen grade of the alpha's output."""
    if not insights:
        print(f"  [{alpha_name}] emitted 0 insights — FAIL")
        return

    longs = [i for i in insights if i.direction == 1]
    shorts = [i for i in insights if i.direction == -1]
    flats = [i for i in insights if i.direction == 0]

    print(
        f"  [{alpha_name}] {len(insights)} insights "
        f"({len(longs)}L / {len(shorts)}S / {len(flats)}F)"
    )

    if insights:
        mags = sorted((i.magnitude for i in insights if i.magnitude is not None), reverse=True)

        if mags:
            print(
                f"      magnitude: min={mags[-1]:.4f}  median={mags[len(mags) // 2]:.4f}  max={mags[0]:.4f}"
            )

    # Reason: show the top-2 long and top-2 short by magnitude so we can eyeball
    # whether the alpha is picking sensible names.
    sorted_longs = sorted(longs, key=lambda i: i.magnitude or 0, reverse=True)
    sorted_shorts = sorted(shorts, key=lambda i: i.magnitude or 0, reverse=True)

    if sorted_longs:
        top = sorted_longs[:2]
        print(
            f"      top longs:  "
            + ", ".join(f"{i.symbol} (|m|={i.magnitude:.4f})" for i in top)
        )

    if sorted_shorts:
        top = sorted_shorts[:2]
        print(
            f"      top shorts: "
            + ", ".join(f"{i.symbol} (|m|={i.magnitude:.4f})" for i in top)
        )

    # Reason: every insight should satisfy invariants — contract check.
    for insight in insights:
        assert insight.source_alpha == alpha_name, f"source_alpha mismatch for {insight.symbol}"
        assert insight.direction in (-1, 0, 1), f"bad direction {insight.direction} for {insight.symbol}"
        assert insight.magnitude is None or insight.magnitude >= 0, \
            f"negative magnitude {insight.magnitude} for {insight.symbol}"
        assert insight.close_time > insight.generated_time, \
            f"close_time not in future for {insight.symbol}"


def _sanity_check_momentum(
    insights: list[Insight], data: dict[str, pd.DataFrame], asof: datetime,
) -> None:
    """For momentum, the sign should match the 12-1 return sign directly."""
    failures = 0

    for insight in insights:
        df = data[insight.symbol].loc[data[insight.symbol].index <= pd.Timestamp(asof)]
        closes = df["close"]

        if len(closes) < 253:
            continue

        start = float(closes.iloc[-253])
        end = float(closes.iloc[-22])
        expected_return = (end / start) - 1.0

        expected_dir = 1 if expected_return > 0 else -1 if expected_return < 0 else 0

        if insight.direction != expected_dir:
            failures += 1
            print(
                f"      MISMATCH {insight.symbol}: direction={insight.direction} "
                f"but 12-1 return={expected_return:+.4f}"
            )

    if failures == 0:
        print("      momentum direction check: OK (all signs match 12-1 return)")
    else:
        print(f"      momentum direction check: FAIL ({failures} mismatches)")


def _sanity_check_low_vol(insights: list[Insight]) -> None:
    """Cross-sectional: long/short count should be roughly balanced."""
    if not insights:
        return

    longs = [i for i in insights if i.direction == 1]
    shorts = [i for i in insights if i.direction == -1]

    # Reason: longs = below-median-vol, shorts = above-median-vol.
    # With even universe size, count should be roughly balanced.
    ratio = len(longs) / max(len(longs) + len(shorts), 1)
    balanced = 0.3 <= ratio <= 0.7

    print(
        f"      long/short balance: {len(longs)}L vs {len(shorts)}S "
        f"(ratio={ratio:.2f}) -> {'OK' if balanced else 'SKEWED'}"
    )


def _run_alpha(
    alpha: AlphaModel,
    data: dict[str, pd.DataFrame],
    asof: datetime,
) -> list[Insight]:
    ctx = _build_context(data, asof)
    return alpha.update(ctx)


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    data = _load_bars()

    if not data:
        print("No data — aborting")
        sys.exit(1)

    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    print(f"\nEvaluating alphas at asof = {asof.date()}\n")

    # --- Momentum
    mom_insights = _run_alpha(MomentumAlpha(), data, asof)
    _grade(mom_insights, "momentum")
    _sanity_check_momentum(mom_insights, data, asof)

    # --- Breakout
    brk_insights = _run_alpha(BreakoutAlpha(), data, asof)
    _grade(brk_insights, "breakout")

    # --- Reversal
    rev_insights = _run_alpha(ShortTermReversalAlpha(), data, asof)
    _grade(rev_insights, "reversal")

    # --- Low-vol (cross-sectional)
    lv_insights = _run_alpha(LowVolAlpha(), data, asof)
    _grade(lv_insights, "low_vol")
    _sanity_check_low_vol(lv_insights)

    # --- Trend-volume
    tv_insights = _run_alpha(TrendVolumeAlpha(), data, asof)
    _grade(tv_insights, "trend_vol")

    print("\n✓ All alphas ran. Contract checks passed.")


if __name__ == "__main__":
    main()
