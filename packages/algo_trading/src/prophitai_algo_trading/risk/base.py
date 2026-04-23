"""Base risk rule contract.

Risk rules are per-bar gates: they either block a proposed entry or force
an exit on an open position. The engine iterates all registered rules and
short-circuits on the first rule that fires.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import datetime

import pandas as pd


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


class RiskRule(ABC):
    """Abstract base for risk rules.

    Subclasses override ``block_entry`` and/or ``force_exit``. Default
    implementations are no-ops so you only write what you need.

    Optional lifecycle hooks — override when state must be tracked:
        on_entry(ctx): called after a position opens.
        on_exit(ctx): called after a position closes.
        on_bar(ctx):  called on every bar the symbol is in the universe.
    """

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
