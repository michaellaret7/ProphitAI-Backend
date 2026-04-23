"""Trading window rule — only permit entries during specific clock hours."""

from __future__ import annotations

from datetime import time

from prophitai_algo_trading.risk.base import RiskContext, RiskRule


class TradingWindow(RiskRule):
    """Block entries outside a ``start`` — ``end`` time window.

    Uses the bar timestamp's time-of-day directly (no timezone conversion).
    Callers supply bars in the relevant trading timezone.

    Args:
        start: Window open (inclusive).
        end: Window close (inclusive).
    """

    def __init__(self, start: time, end: time):
        if start >= end:
            raise ValueError("start must be < end")

        super().__init__()
        self.start = start
        self.end = end

    def block_entry(self, ctx: RiskContext) -> bool:
        ts = ctx.timestamp.time() if hasattr(ctx.timestamp, "time") else None

        if ts is None:
            return False

        return not (self.start <= ts <= self.end)
