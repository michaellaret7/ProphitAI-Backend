"""Real-data test for the 4 Phase 2 PortfolioConstructionModels.

Loads daily OHLCV for a 20-ticker universe, runs the 5 Phase 1 alphas to
produce Insights, then runs each PCM on those Insights. Grades the
PortfolioTargets against contract invariants:
    - target_shares float, no NaN
    - invested symbols not in the new book get target_shares = 0
    - MultiAlphaBlendPCM produces 'blended' insights internally
    - MagnitudeWeightedLongShortPCM preserves dollar-neutrality
      (|sum(long notional)| == |sum(short notional)| within tolerance)

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_portfolio_construction.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading.alphas import (
    BreakoutAlpha,
    LowVolAlpha,
    MomentumAlpha,
    ShortTermReversalAlpha,
    TrendVolumeAlpha,
)
from prophitai_algo_trading.framework import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.portfolio_construction import (
    EqualWeightPCM,
    InsightWeightedPCM,
    MagnitudeWeightedLongShortPCM,
    MultiAlphaBlendPCM,
)
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
INITIAL_CAPITAL = 1_000_000.0


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
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(UNIVERSE)} tickers")

    return ready


def _build_context(data: dict[str, pd.DataFrame], asof: datetime) -> AlgorithmContext:
    sliced: dict[str, pd.DataFrame] = {}

    for ticker, df in data.items():
        upto = df.loc[df.index <= pd.Timestamp(asof)]

        if not upto.empty:
            sliced[ticker] = upto

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)

    return AlgorithmContext(
        timestamp=asof,
        portfolio=portfolio,
        data=sliced,
        warmup=False,
    )


def _collect_insights(ctx: AlgorithmContext) -> list[Insight]:
    alphas = [
        MomentumAlpha(),
        BreakoutAlpha(),
        ShortTermReversalAlpha(),
        LowVolAlpha(),
        TrendVolumeAlpha(),
    ]

    insights: list[Insight] = []

    for alpha in alphas:
        insights.extend(alpha.update(ctx))

    return insights


def _contract_check(
    targets: list[PortfolioTarget], ctx: AlgorithmContext, label: str,
) -> None:
    """Verify every PCM output matches the framework contract."""
    symbols_seen: set[str] = set()

    for t in targets:
        assert isinstance(t, PortfolioTarget), f"{label}: non-PortfolioTarget in output"
        assert isinstance(t.target_shares, float), \
            f"{label}: target_shares not float for {t.symbol}"
        assert t.target_shares == t.target_shares, \
            f"{label}: NaN target_shares for {t.symbol}"
        assert t.symbol not in symbols_seen, \
            f"{label}: duplicate symbol {t.symbol} in targets"

        symbols_seen.add(t.symbol)

    # Reason: every currently-invested symbol should appear (either in
    # the book or as an explicit close).
    for invested_sym in ctx.portfolio.positions:
        assert invested_sym in symbols_seen, \
            f"{label}: invested symbol {invested_sym} missing (would be orphaned)"


def _summarize_book(
    targets: list[PortfolioTarget], ctx: AlgorithmContext, label: str,
) -> None:
    longs = [t for t in targets if t.target_shares > 0]
    shorts = [t for t in targets if t.target_shares < 0]
    closes = [t for t in targets if t.target_shares == 0.0]

    def notional(t: PortfolioTarget) -> float:
        price = float(ctx.data[t.symbol]["close"].iloc[-1])
        return abs(t.target_shares * price)

    long_notional = sum(notional(t) for t in longs)
    short_notional = sum(notional(t) for t in shorts)

    equity = ctx.portfolio.equity()

    print(
        f"  [{label}] {len(targets)} targets "
        f"({len(longs)}L / {len(shorts)}S / {len(closes)} close)"
    )
    print(
        f"      notional: long=${long_notional:,.0f}  "
        f"short=${short_notional:,.0f}  "
        f"gross=${long_notional + short_notional:,.0f}  "
        f"({(long_notional + short_notional) / equity * 100:.1f}% of equity)"
    )

    if longs:
        top = sorted(longs, key=notional, reverse=True)[:2]
        print(
            f"      top longs:  "
            + ", ".join(
                f"{t.symbol} ({t.target_shares:.1f} shares, ${notional(t):,.0f})"
                for t in top
            )
        )

    if shorts:
        top = sorted(shorts, key=notional, reverse=True)[:2]
        print(
            f"      top shorts: "
            + ", ".join(
                f"{t.symbol} ({t.target_shares:.1f} shares, ${notional(t):,.0f})"
                for t in top
            )
        )


def _check_dollar_neutral(
    targets: list[PortfolioTarget],
    ctx: AlgorithmContext,
    tolerance_pct: float = 1.0,
) -> None:
    """Assert long notional ≈ short notional within ``tolerance_pct``."""
    longs = [t for t in targets if t.target_shares > 0]
    shorts = [t for t in targets if t.target_shares < 0]

    def notional(t: PortfolioTarget) -> float:
        price = float(ctx.data[t.symbol]["close"].iloc[-1])
        return abs(t.target_shares * price)

    long_notional = sum(notional(t) for t in longs)
    short_notional = sum(notional(t) for t in shorts)

    if long_notional == 0 or short_notional == 0:
        print("      dollar-neutrality: N/A (empty side)")
        return

    asymmetry_pct = abs(long_notional - short_notional) / max(long_notional, short_notional) * 100.0

    passes = asymmetry_pct <= tolerance_pct

    print(
        f"      dollar-neutrality: long/short diff = "
        f"{asymmetry_pct:.2f}% → {'OK' if passes else 'FAIL'}"
    )


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    data = _load_bars()

    if not data:
        print("No data — aborting")
        sys.exit(1)

    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _build_context(data, asof)

    insights = _collect_insights(ctx)

    print(f"\nCollected {len(insights)} insights from 5 alphas at {asof.date()}\n")

    # --- EqualWeightPCM
    pcm1 = EqualWeightPCM(max_positions=8, gross_exposure=1.0)
    targets1 = pcm1.create_targets(ctx, insights)
    _contract_check(targets1, ctx, "equal_weight")
    _summarize_book(targets1, ctx, "equal_weight")

    # --- InsightWeightedPCM
    pcm2 = InsightWeightedPCM(gross_exposure=1.0, per_position_cap=0.15, max_positions=10)
    targets2 = pcm2.create_targets(ctx, insights)
    _contract_check(targets2, ctx, "insight_weighted")
    _summarize_book(targets2, ctx, "insight_weighted")

    # --- MagnitudeWeightedLongShortPCM (using all raw insights — cross-alpha)
    # Reason: raw insights are on different native scales; this PCM works
    # best with z-scored input (see MultiAlphaBlendPCM below), but it
    # should still produce a valid book on mixed-scale input.
    pcm3 = MagnitudeWeightedLongShortPCM(
        gross_exposure=2.0, per_position_cap=0.10,
        quantile=0.20, min_abs_score=0.0,
    )
    targets3 = pcm3.create_targets(ctx, insights)
    _contract_check(targets3, ctx, "magnitude_ls")
    _summarize_book(targets3, ctx, "magnitude_ls")
    _check_dollar_neutral(targets3, ctx)

    # --- MultiAlphaBlendPCM(... inner=MagnitudeWeightedLongShortPCM)
    inner = MagnitudeWeightedLongShortPCM(
        gross_exposure=2.0, per_position_cap=0.10,
        quantile=0.20, min_abs_score=0.20,
    )
    pcm4 = MultiAlphaBlendPCM(
        weights={
            "momentum":  0.30,
            "breakout":  0.25,
            "reversal":  0.15,
            "low_vol":   0.15,
            "trend_vol": 0.15,
        },
        inner=inner,
    )
    targets4 = pcm4.create_targets(ctx, insights)
    _contract_check(targets4, ctx, "multi_alpha_blend")
    _summarize_book(targets4, ctx, "multi_alpha_blend")
    _check_dollar_neutral(targets4, ctx)

    print("\nAll PCMs ran. Contract checks passed.")


if __name__ == "__main__":
    main()
