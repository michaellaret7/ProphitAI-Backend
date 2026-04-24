"""Risk rule base — each rule is a complete RiskManagementModel.

A ``RiskRule`` is self-contained: it defines per-bar hooks
(``block_entry`` / ``force_exit`` / ``on_bar`` / ``on_entry`` / ``on_exit``)
AND implements the ``RiskManagementModel`` protocol through ``manage()``.
No wrapper, no bridge class. Drop a rule straight into
``Algorithm(risk_management=StopLossExit(0.05))`` or compose several via
``CompositeRiskModel``.

Pipeline per ``manage()`` call (all encapsulated in this base):

  1. Update the rule's own equity peak.
  2. Fire ``on_bar`` for every invested symbol so stateful rules refresh.
     If nothing is invested, fire once with a probe symbol so
     portfolio-wide rules still tick.
  3. Walk invested symbols; call ``force_exit``. Any symbol where the
     hook fires is marked for forced close.
  4. Walk the target list:
       a. New-entry targets → drop if ``block_entry`` fires.
       b. Symbols in forced-closes → override ``target_shares=0``.
       c. Pass through otherwise.
  5. For invested symbols in forced-closes but absent from the target
     list, append explicit 0-share targets so Execution closes them.

``on_position_opened`` / ``on_position_closed`` are the engine hooks
that forward position open/close events into ``on_entry`` / ``on_exit``.
They satisfy the ``LifecycleAwareRiskModel`` protocol so the engine
dispatches to them via a single ``isinstance`` gate.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import (
        AlgorithmContext,
        PortfolioTarget,
    )


#     ================================
# --> Helper funcs
#     ================================

def _probe_symbol(targets: list["PortfolioTarget"]) -> str | None:
    """First symbol in the target list, or None if empty."""
    for target in targets:
        return target.symbol

    return None


#     ================================
# --> Peak equity tracker
#     ================================

class PeakEquityTracker:
    """Running peak of portfolio equity, monotonically non-decreasing.

    Owned per-rule. Rules that care about drawdown math read ``peak``;
    rules that don't simply ignore it.
    """

    def __init__(self) -> None:
        self._peak: float = 0.0

    @property
    def peak(self) -> float:
        return self._peak

    def update(self, equity: float) -> float:
        if equity > self._peak:
            self._peak = equity

        return self._peak

    def reset(self, equity: float) -> None:
        """Hard reset — used after a cooldown ends so we don't immediately
        re-trigger on the same drawdown."""
        self._peak = equity


#     ================================
# --> Rule context
#     ================================

@dataclass
class RiskContext:
    """Everything a risk rule can inspect at a single bar.

    Attributes:
        symbol: Ticker being evaluated.
        price: Current bar close.
        timestamp: Bar timestamp.
        df: Indicator-enriched frame up to and including the current bar.
        current_position: 1 (long), -1 (short), 0 (flat).
        entry_price: Entry price if a position is open, else None.
        entry_time: Entry timestamp if a position is open, else None.
        proposed_direction: Direction of a proposed entry (1 or -1), else None.
        portfolio_equity: Current mark-to-market equity.
        portfolio_peak: Running peak equity for drawdown rules.
    """

    symbol: str
    price: float
    timestamp: datetime
    df: pd.DataFrame
    current_position: int = 0
    entry_price: float | None = None
    entry_time: datetime | None = None
    proposed_direction: int | None = None
    portfolio_equity: float = 0.0
    portfolio_peak: float = 0.0


#     ================================
# --> Rule base
#     ================================

class RiskRule(ABC):
    """Self-contained risk rule that satisfies ``RiskManagementModel``.

    Subclasses override whichever hooks they need:

        block_entry(ctx)             → veto a proposed entry
        force_exit(ctx)              → close an open position
        on_bar(ctx)                  → per-bar state refresh
        on_entry(ctx)                → fired after a position opens
        on_exit(ctx, trade_pnl)      → fired after a position closes

    Default implementations are no-ops so subclasses only write what
    they need. The ``manage()`` method below wires those hooks onto the
    PortfolioTarget pipeline — no wrapper required.
    """

    def __init__(self) -> None:
        self._peak_tracker = PeakEquityTracker()

    #     ================================
    # --> Hook surface (override in subclasses)
    #     ================================

    def block_entry(self, ctx: RiskContext) -> bool:
        """Return True to veto the proposed entry."""
        return False

    def force_exit(self, ctx: RiskContext) -> bool:
        """Return True to close the open position this bar."""
        return False

    def on_entry(self, ctx: RiskContext) -> None:
        """Hook — fires after a position opens."""

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        """Hook — fires after a position closes. ``trade_pnl`` is the realized P&L."""

    def on_bar(self, ctx: RiskContext) -> None:
        """Hook — fires every bar per symbol."""

    #     ================================
    # --> RiskManagementModel protocol
    #     ================================

    def manage(
        self,
        ctx: "AlgorithmContext",
        targets: list["PortfolioTarget"],
    ) -> list["PortfolioTarget"]:
        """Apply this rule to the full target list for the current bar."""
        equity = ctx.portfolio.equity()
        peak = self._peak_tracker.update(equity)

        self._fire_on_bar(ctx, targets, peak)

        forced_closes = self._collect_forced_closes(ctx, peak)

        return self._apply_to_targets(ctx, targets, forced_closes, peak)

    def on_position_opened(
        self, ctx: "AlgorithmContext", symbol: str,
    ) -> None:
        """Forward an open-position event into ``on_entry``."""
        rule_ctx = self._build_rule_context(
            ctx, symbol, portfolio_peak=self._peak_tracker.peak,
        )

        self.on_entry(rule_ctx)

    def on_position_closed(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        pnl: float,
    ) -> None:
        """Forward a close-position event into ``on_exit``."""
        rule_ctx = self._build_rule_context(
            ctx, symbol, portfolio_peak=self._peak_tracker.peak,
        )

        self.on_exit(rule_ctx, pnl)

    #     ================================
    # --> Internal pipeline
    #     ================================

    def _fire_on_bar(
        self,
        ctx: "AlgorithmContext",
        targets: list["PortfolioTarget"],
        peak: float,
    ) -> None:
        """Refresh rule state for the current bar."""
        invested = list(ctx.portfolio.positions)

        if invested:
            for symbol in invested:
                rule_ctx = self._build_rule_context(ctx, symbol, portfolio_peak=peak)

                self.on_bar(rule_ctx)

            return

        # Reason: no positions — portfolio-wide rules still need a tick
        # (DailyLossLimit's day-start-equity tracker) so fire once with
        # a probe symbol pulled from the target list.
        probe = _probe_symbol(targets)

        if probe is None:
            return

        rule_ctx = self._build_rule_context(ctx, probe, portfolio_peak=peak)

        self.on_bar(rule_ctx)

    def _collect_forced_closes(
        self,
        ctx: "AlgorithmContext",
        peak: float,
    ) -> set[str]:
        forced: set[str] = set()

        for symbol in ctx.portfolio.positions:
            rule_ctx = self._build_rule_context(ctx, symbol, portfolio_peak=peak)

            if self.force_exit(rule_ctx):
                forced.add(symbol)

        return forced

    def _apply_to_targets(
        self,
        ctx: "AlgorithmContext",
        targets: list["PortfolioTarget"],
        forced_closes: set[str],
        peak: float,
    ) -> list["PortfolioTarget"]:
        from prophitai_algo_trading.core.models import PortfolioTarget

        out: list[PortfolioTarget] = []
        present: set[str] = set()

        for target in targets:
            present.add(target.symbol)

            invested = ctx.portfolio.get_position(target.symbol) != 0
            is_new_entry = target.target_shares != 0.0 and not invested

            if is_new_entry and self._blocked(ctx, target, peak):
                continue

            if target.symbol in forced_closes:
                out.append(PortfolioTarget(target.symbol, 0.0))
                continue

            out.append(target)

        for symbol in forced_closes:
            if symbol not in present:
                out.append(PortfolioTarget(symbol, 0.0))

        return out

    def _blocked(
        self,
        ctx: "AlgorithmContext",
        target: "PortfolioTarget",
        peak: float,
    ) -> bool:
        direction = 1 if target.target_shares > 0 else -1

        rule_ctx = self._build_rule_context(
            ctx, target.symbol,
            proposed_direction=direction,
            portfolio_peak=peak,
        )

        return self.block_entry(rule_ctx)

    def _build_rule_context(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        proposed_direction: int | None = None,
        portfolio_peak: float = 0.0,
    ) -> RiskContext:
        """Pull per-symbol price and position state off AlgorithmContext."""
        df = ctx.data.get(symbol, pd.DataFrame())
        price = float(df["close"].iloc[-1]) if not df.empty else 0.0

        position = ctx.portfolio.positions.get(symbol)

        return RiskContext(
            symbol=symbol,
            price=price,
            timestamp=ctx.timestamp,
            df=df,
            current_position=position.direction if position else 0,
            entry_price=position.entry_price if position else None,
            entry_time=position.entry_time if position else None,
            proposed_direction=proposed_direction,
            portfolio_equity=ctx.portfolio.equity(),
            portfolio_peak=portfolio_peak,
        )
