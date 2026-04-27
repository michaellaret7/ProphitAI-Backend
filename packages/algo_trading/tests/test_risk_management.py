"""Real-data + targeted test for the 5 Phase 3 RiskManagementModels.

Two halves:
  1. INTEGRATION: load real OHLCV, run Alpha -> PCM -> Risk pipeline,
     verify output contract invariants.
  2. TARGETED: construct specific scenarios that MUST trigger each
     risk model (drawdown delever, gross cap, stop-loss force exit,
     daily loss limit block), assert behavior.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_risk_management.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading.alpha_signals import (
    BreakoutAlpha,
    LowVolAlpha,
    MomentumAlpha,
    ShortTermReversalAlpha,
    TrendVolumeAlpha,
)
from prophitai_algo_trading.core import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.construction import (
    MagnitudeWeightedLongShortPCM,
    MultiAlphaBlendPCM,
)
from prophitai_algo_trading.portfolio.portfolio import Portfolio, Position
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    DailyLossLimit,
    MaxDrawdownRiskModel,
    MaxGrossExposureRiskModel,
    StopLossExit,
)
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


UNIVERSE = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "JPM"]
START = "2023-06-01"
END = "2024-12-31"


#     ================================
# --> Real-data loader
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


def _build_context(
    data: dict[str, pd.DataFrame],
    asof: datetime,
    portfolio: Portfolio | None = None,
) -> AlgorithmContext:
    sliced: dict[str, pd.DataFrame] = {}
    for ticker, df in data.items():
        upto = df.loc[df.index <= pd.Timestamp(asof)]
        if not upto.empty:
            sliced[ticker] = upto

    return AlgorithmContext(
        timestamp=asof,
        portfolio=portfolio or Portfolio(initial_capital=1_000_000.0),
        data=sliced,
        warmup=False,
    )


#     ================================
# --> Contract check
#     ================================

def _contract_check(targets: list[PortfolioTarget], label: str) -> None:
    seen: set[str] = set()
    for t in targets:
        assert isinstance(t.target_shares, float), f"{label}: non-float"
        assert t.target_shares == t.target_shares, f"{label}: NaN in {t.symbol}"
        assert t.symbol not in seen, f"{label}: duplicate symbol {t.symbol}"
        seen.add(t.symbol)


#     ================================
# --> Integration: Alpha → PCM → Risk
#     ================================

def test_integration_pipeline() -> None:
    print("\n--- INTEGRATION: Alpha -> PCM -> Risk pipeline ---")
    data = _load_bars()
    if not data:
        print("No data; skipping")
        return

    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _build_context(data, asof)

    alphas = [MomentumAlpha(), BreakoutAlpha(), ShortTermReversalAlpha(),
              LowVolAlpha(), TrendVolumeAlpha()]
    insights: list[Insight] = []
    for alpha in alphas:
        insights.extend(alpha.update(ctx))

    pcm = MultiAlphaBlendPCM(
        weights={"momentum": 0.3, "breakout": 0.25, "reversal": 0.15,
                 "low_vol": 0.15, "trend_vol": 0.15},
        inner=MagnitudeWeightedLongShortPCM(
            gross_exposure=2.5, per_position_cap=0.15,
            quantile=0.25, min_abs_score=0.0,
        ),
    )
    targets = pcm.create_targets(ctx, insights)

    risk = CompositeRiskModel([
        MaxDrawdownRiskModel(max_drawdown_pct=0.15),
        MaxGrossExposureRiskModel(max_gross=2.0),
    ])
    final = risk.manage(ctx, targets)

    _contract_check(final, "integration")

    equity = ctx.portfolio.equity()
    gross_before = sum(
        abs(t.target_shares) * float(ctx.data[t.symbol]["close"].iloc[-1])
        for t in targets
    )
    gross_after = sum(
        abs(t.target_shares) * float(ctx.data[t.symbol]["close"].iloc[-1])
        for t in final
    )

    print(f"  targets in: {len(targets)}   gross ${gross_before:,.0f} ({gross_before/equity*100:.1f}% of equity)")
    print(f"  targets out: {len(final)}  gross ${gross_after:,.0f} ({gross_after/equity*100:.1f}% of equity)")

    ratio = gross_after / equity
    print(f"  gross cap respected: {ratio:.2f}x <= 2.00x  {'OK' if ratio <= 2.01 else 'FAIL'}")


#     ================================
# --> Targeted: drawdown delever
#     ================================

def test_drawdown_delever() -> None:
    print("\n--- TARGETED: MaxDrawdownRiskModel delever triggers on 20% drop ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _build_context(data, asof)

    model = MaxDrawdownRiskModel(
        max_drawdown_pct=0.15, delever_factor=0.5, cooldown_days=30,
    )

    # Bar 1: equity = 1M, targets pass through (establish peak).
    targets_in = [PortfolioTarget("AAPL", 100.0), PortfolioTarget("MSFT", -50.0)]
    out1 = model.manage(ctx, targets_in)
    assert out1[0].target_shares == 100.0, "no delever expected before drawdown"
    print(f"  bar 1 (equity $1.00M): 100 AAPL -> {out1[0].target_shares:.1f}  OK")

    # Simulate equity drop by instantiating a new portfolio with fewer funds.
    # A 20% drawdown should trigger delever.
    drawdown_portfolio = Portfolio(initial_capital=800_000.0)
    ctx2 = _build_context(data, asof, portfolio=drawdown_portfolio)

    out2 = model.manage(ctx2, targets_in)
    # Peak was established at 1M (bar 1); now equity 800k = -20% dd; delever = 0.5
    expected = 100.0 * 0.5
    assert abs(out2[0].target_shares - expected) < 1e-9, \
        f"expected delever to {expected}, got {out2[0].target_shares}"
    print(f"  bar 2 (equity $0.80M, -20% DD): 100 AAPL -> {out2[0].target_shares:.1f} (delever 0.5x)  OK")

    # Fast-forward past cooldown
    ctx3 = _build_context(
        data, asof + timedelta(days=31),
        portfolio=Portfolio(initial_capital=750_000.0),
    )
    out3 = model.manage(ctx3, targets_in)
    # Cooldown expired, peak reset to 750k; no delever.
    assert out3[0].target_shares == 100.0, \
        f"post-cooldown should pass through, got {out3[0].target_shares}"
    print(f"  bar 3 (post-cooldown, peak reset): 100 AAPL -> {out3[0].target_shares:.1f}  OK")


#     ================================
# --> Targeted: gross cap
#     ================================

def test_gross_cap() -> None:
    print("\n--- TARGETED: MaxGrossExposureRiskModel scales when over cap ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _build_context(data, asof)

    # Make targets totaling > 2x gross
    equity = ctx.portfolio.equity()
    prices = {s: float(df["close"].iloc[-1]) for s, df in ctx.data.items()}

    # Each of 4 positions at 75% of equity = 300% gross
    heavy_targets = [
        PortfolioTarget("AAPL", (equity * 0.75) / prices["AAPL"]),
        PortfolioTarget("MSFT", -(equity * 0.75) / prices["MSFT"]),
        PortfolioTarget("NVDA", (equity * 0.75) / prices["NVDA"]),
        PortfolioTarget("META", -(equity * 0.75) / prices["META"]),
    ]

    model = MaxGrossExposureRiskModel(max_gross=2.0)
    out = model.manage(ctx, heavy_targets)

    gross = sum(abs(t.target_shares) * prices[t.symbol] for t in out)
    ratio = gross / equity

    print(f"  input gross: 3.00x   output gross: {ratio:.2f}x")
    assert abs(ratio - 2.0) < 1e-6, f"expected 2.0x gross after cap, got {ratio}"
    print(f"  gross cap: OK")


#     ================================
# --> Targeted: stop loss force exit
#     ================================

def test_position_stops_force_exit() -> None:
    print("\n--- TARGETED: StopLossExit forces exit on stop breach ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    # Seed a long AAPL position at an entry price well above current close.
    # 5% stop with entry at 2x current price -> stop triggers immediately.
    portfolio = Portfolio(initial_capital=1_000_000.0)
    current_price = float(data["AAPL"]["close"].iloc[-1])
    entry_price = current_price * 2.0  # 50% loss, way past 5% stop

    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=entry_price, entry_time=asof - timedelta(days=10),
        entry_cost=0.0,
    )

    ctx = _build_context(data, asof, portfolio=portfolio)

    # Target says "keep the position" (100 shares long)
    targets_in = [PortfolioTarget("AAPL", 100.0)]

    model = StopLossExit(pct=0.05)
    out = model.manage(ctx, targets_in)

    aapl_targets = [t for t in out if t.symbol == "AAPL"]
    assert len(aapl_targets) == 1, "expected one AAPL target"
    assert aapl_targets[0].target_shares == 0.0, \
        f"expected 0 shares after stop, got {aapl_targets[0].target_shares}"
    print(f"  AAPL @ entry ${entry_price:.2f}, now ${current_price:.2f} (-50%)")
    print(f"  StopLossExit(5%) forced AAPL target to {aapl_targets[0].target_shares}  OK")


#     ================================
# --> Targeted: portfolio-level block
#     ================================

def test_portfolio_limits_block() -> None:
    print("\n--- TARGETED: DailyLossLimit blocks new entries after daily loss ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    # Simulate a mid-day 5% drawdown on $1M start equity.
    # DailyLossLimit at 3% should trigger.
    portfolio = Portfolio(initial_capital=1_000_000.0)

    # Fire on_bar once with start-of-day equity = 1M
    ctx_morning = _build_context(data, asof, portfolio=portfolio)
    model = DailyLossLimit(loss_pct=0.03)

    # Morning: pass through, establish day start equity
    targets_in = [PortfolioTarget("AAPL", 100.0)]
    out1 = model.manage(ctx_morning, targets_in)
    assert len(out1) == 1, "morning should pass through"
    print(f"  morning (equity $1.00M): 1 target -> {len(out1)} targets  OK")

    # Afternoon: same day, equity dropped 5%
    portfolio_afternoon = Portfolio(initial_capital=950_000.0)
    ctx_afternoon = _build_context(data, asof, portfolio=portfolio_afternoon)

    out2 = model.manage(ctx_afternoon, targets_in)
    # New entry (AAPL, not invested) should be dropped
    assert len(out2) == 0, \
        f"expected 0 targets after -5% daily loss, got {len(out2)}"
    print(f"  afternoon (equity $0.95M, -5% day): 1 target -> {len(out2)} targets (blocked)  OK")


#     ================================
# --> Targeted: composite ordering
#     ================================

def test_composite_ordering() -> None:
    print("\n--- TARGETED: CompositeRiskModel runs models in declared order ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _build_context(data, asof)

    # Build targets that are 3x gross. Expect both drawdown-delever (inactive
    # since no drawdown) and gross cap to apply cleanly.
    equity = ctx.portfolio.equity()
    prices = {s: float(df["close"].iloc[-1]) for s, df in ctx.data.items()}

    targets = [
        PortfolioTarget("AAPL", (equity * 1.0) / prices["AAPL"]),
        PortfolioTarget("MSFT", -(equity * 1.0) / prices["MSFT"]),
        PortfolioTarget("NVDA", (equity * 0.5) / prices["NVDA"]),
        PortfolioTarget("META", -(equity * 0.5) / prices["META"]),
    ]

    composite = CompositeRiskModel([
        MaxDrawdownRiskModel(max_drawdown_pct=0.15),  # no-op (no DD)
        MaxGrossExposureRiskModel(max_gross=2.0),     # should cap 3x -> 2x
    ])

    out = composite.manage(ctx, targets)

    gross = sum(abs(t.target_shares) * prices[t.symbol] for t in out)
    ratio = gross / equity

    assert abs(ratio - 2.0) < 1e-6, f"expected 2x gross, got {ratio:.3f}"
    print(f"  composite (DD + gross cap) scaled 3.00x -> {ratio:.2f}x  OK")


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    test_integration_pipeline()
    test_drawdown_delever()
    test_gross_cap()
    test_position_stops_force_exit()
    test_portfolio_limits_block()
    test_composite_ordering()
    print("\nAll risk-management tests passed.")


if __name__ == "__main__":
    main()
