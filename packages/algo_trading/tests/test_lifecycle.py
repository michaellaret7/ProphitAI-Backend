"""Boundary tests for ``engines.lifecycle`` — position diff + emit.

Synthesizes before/after portfolio states by hand, constructs a
mock risk model, calls ``emit_lifecycle``, and asserts the correct
``on_position_opened`` / ``on_position_closed`` invocations for every
diff shape: no-change, entry (flat -> held), exit (held -> flat), flip
(long -> short), and the ``isinstance`` gating for non-lifecycle-aware
risk models.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_lifecycle.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading.engines.lifecycle import (
    emit_lifecycle,
    snapshot_positions,
)
from prophitai_algo_trading.core import (
    AlgorithmContext,
    PortfolioTarget,
)
from prophitai_algo_trading.accounting.portfolio import Portfolio, Position, Trade


ASOF = datetime(2024, 12, 31, 0, 0, 0)


#     ================================
# --> Mocks
#     ================================

class RecordingRiskModel:
    """Lifecycle-aware mock — records every opened / closed call."""

    def __init__(self) -> None:
        self.opens: list[tuple[str]] = []
        self.closes: list[tuple[str, float]] = []

    def manage(
        self, ctx: AlgorithmContext, targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        return targets

    def on_position_opened(
        self, ctx: AlgorithmContext, symbol: str,
    ) -> None:
        self.opens.append((symbol,))

    def on_position_closed(
        self, ctx: AlgorithmContext, symbol: str, pnl: float,
    ) -> None:
        self.closes.append((symbol, pnl))


class BareRiskModel:
    """Non-lifecycle-aware mock — only implements .manage."""

    def manage(
        self, ctx: AlgorithmContext, targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        return targets


#     ================================
# --> Helpers
#     ================================

def _make_portfolio(positions: dict[str, tuple[int, float]]) -> Portfolio:
    """Build a Portfolio seeded with ``{symbol: (direction, shares)}``."""
    p = Portfolio(initial_capital=1_000_000.0)

    for symbol, (direction, shares) in positions.items():
        p.positions[symbol] = Position(
            symbol=symbol, shares=shares, direction=direction,
            entry_price=100.0, entry_time=ASOF, entry_cost=0.0,
        )

    return p


def _make_ctx(portfolio: Portfolio) -> AlgorithmContext:
    return AlgorithmContext(
        timestamp=ASOF, portfolio=portfolio, data={}, warmup=False,
    )


def _seed_trade(portfolio: Portfolio, symbol: str, pnl: float) -> None:
    """Append a Trade record so emit_lifecycle can look up pnl."""
    portfolio.trades.append(Trade(
        symbol=symbol, direction=1, entry_time=ASOF, exit_time=ASOF,
        entry_price=100.0, exit_price=110.0, shares=10.0,
        pnl=pnl, return_pct=10.0,
    ))


#     ================================
# --> Diff scenarios
#     ================================

def test_snapshot_emits_only_open_positions() -> None:
    print("\n--- snapshot_positions: flat symbols omitted ---")
    p = _make_portfolio({"AAPL": (1, 100.0), "MSFT": (-1, 50.0)})

    snap = snapshot_positions(p)

    assert snap == {"AAPL": 1, "MSFT": -1}, f"unexpected snapshot: {snap}"
    print(f"  snapshot = {snap}  OK")


def test_entry_fires_on_position_opened() -> None:
    print("\n--- entry (flat -> long): fires on_position_opened only ---")
    p_after = _make_portfolio({"AAPL": (1, 100.0)})
    ctx = _make_ctx(p_after)

    risk = RecordingRiskModel()
    before: dict[str, int] = {}  # flat before
    emit_lifecycle(risk, ctx, before, trades_before=0)

    assert risk.opens == [("AAPL",)], f"expected one open, got {risk.opens}"
    assert risk.closes == [], f"expected no closes, got {risk.closes}"
    print(f"  opens={risk.opens}  closes={risk.closes}  OK")


def test_exit_fires_on_position_closed_with_pnl() -> None:
    print("\n--- exit (long -> flat): fires on_position_closed with PnL ---")
    p_after = Portfolio(initial_capital=1_000_000.0)  # no positions after
    _seed_trade(p_after, "AAPL", pnl=250.0)
    ctx = _make_ctx(p_after)

    risk = RecordingRiskModel()
    before = {"AAPL": 1}  # long before
    emit_lifecycle(risk, ctx, before, trades_before=0)

    assert risk.opens == [], f"expected no opens, got {risk.opens}"
    assert risk.closes == [("AAPL", 250.0)], \
        f"expected one close with pnl=250, got {risk.closes}"
    print(f"  closes={risk.closes}  OK")


def test_flip_fires_both_close_and_open() -> None:
    print("\n--- flip (long -> short): fires BOTH close and open ---")
    p_after = _make_portfolio({"AAPL": (-1, 100.0)})
    _seed_trade(p_after, "AAPL", pnl=-75.0)
    ctx = _make_ctx(p_after)

    risk = RecordingRiskModel()
    before = {"AAPL": 1}  # long before, short after
    emit_lifecycle(risk, ctx, before, trades_before=0)

    assert risk.closes == [("AAPL", -75.0)], \
        f"expected close with pnl=-75, got {risk.closes}"
    assert risk.opens == [("AAPL",)], f"expected open after flip, got {risk.opens}"
    print(f"  closes={risk.closes}  opens={risk.opens}  OK")


def test_no_change_fires_nothing() -> None:
    print("\n--- no change (long -> long, same size): fires nothing ---")
    p_after = _make_portfolio({"AAPL": (1, 100.0)})
    ctx = _make_ctx(p_after)

    risk = RecordingRiskModel()
    before = {"AAPL": 1}
    emit_lifecycle(risk, ctx, before, trades_before=0)

    assert risk.opens == [] and risk.closes == [], \
        f"expected no events, got opens={risk.opens}, closes={risk.closes}"
    print("  no events  OK")


def test_non_lifecycle_aware_risk_model_skipped() -> None:
    print("\n--- non-lifecycle-aware risk model: emit_lifecycle is a no-op ---")
    p_after = _make_portfolio({"AAPL": (1, 100.0)})
    ctx = _make_ctx(p_after)

    risk = BareRiskModel()
    before: dict[str, int] = {}
    emit_lifecycle(risk, ctx, before, trades_before=0)
    # If we got here, no AttributeError fired when the model lacked the hooks.
    print("  no exception raised, bare model silently skipped  OK")


def test_pnl_only_from_trades_after_trades_before() -> None:
    print("\n--- PnL lookup isolates trades produced during this step ---")
    p_after = Portfolio(initial_capital=1_000_000.0)
    # Seed an old trade that must be ignored.
    _seed_trade(p_after, "AAPL", pnl=999.0)
    trades_before = len(p_after.trades)
    # Now the "new" trade from this step.
    _seed_trade(p_after, "AAPL", pnl=50.0)
    ctx = _make_ctx(p_after)

    risk = RecordingRiskModel()
    before = {"AAPL": 1}
    emit_lifecycle(risk, ctx, before, trades_before=trades_before)

    assert risk.closes == [("AAPL", 50.0)], \
        f"expected pnl from post-trades_before only, got {risk.closes}"
    print(f"  closes={risk.closes}  (old pnl=999 correctly ignored)  OK")


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    test_snapshot_emits_only_open_positions()
    test_entry_fires_on_position_opened()
    test_exit_fires_on_position_closed_with_pnl()
    test_flip_fires_both_close_and_open()
    test_no_change_fires_nothing()
    test_non_lifecycle_aware_risk_model_skipped()
    test_pnl_only_from_trades_after_trades_before()

    print("\nAll lifecycle tests passed.")


if __name__ == "__main__":
    main()
