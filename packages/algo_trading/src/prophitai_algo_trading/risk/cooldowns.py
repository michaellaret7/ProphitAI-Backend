"""Cooldown rules: ReentryCooldown and ConsecutiveLossCooldown."""

from __future__ import annotations

from datetime import datetime

from prophitai_algo_trading.risk.base import RiskContext, RiskRule


class ReentryCooldown(RiskRule):
    """Block new entries on a symbol for ``bars`` bars after its last exit.

    Args:
        bars: Cooldown duration in bars.
    """

    def __init__(self, bars: int):
        if bars < 0:
            raise ValueError("bars must be >= 0.")

        self.bars = bars
        self._last_exit_bar: dict[str, int] = {}

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        self._last_exit_bar[ctx.symbol] = len(ctx.df) - 1

    def block_entry(self, ctx: RiskContext) -> bool:
        last_exit = self._last_exit_bar.get(ctx.symbol)

        if last_exit is None:
            return False

        return (len(ctx.df) - 1) - last_exit < self.bars


class ConsecutiveLossCooldown(RiskRule):
    """Block entries across all symbols for ``bars`` bars after N consecutive losses.

    Args:
        max_losses: Threshold of consecutive losing trades that triggers the cooldown.
        bars: Cooldown duration in bars once triggered.
    """

    def __init__(self, max_losses: int, bars: int):
        if max_losses < 1:
            raise ValueError("max_losses must be >= 1.")
        if bars < 0:
            raise ValueError("bars must be >= 0.")

        self.max_losses = max_losses
        self.bars = bars
        self._streak = 0
        self._cooldown_start: datetime | None = None
        self._cooldown_start_bars: int | None = None

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        if trade_pnl < 0:
            self._streak += 1

            if self._streak >= self.max_losses:
                self._cooldown_start = ctx.timestamp
                self._cooldown_start_bars = len(ctx.df) - 1
        else:
            self._streak = 0

    def block_entry(self, ctx: RiskContext) -> bool:
        if self._cooldown_start_bars is None:
            return False

        bars_elapsed = (len(ctx.df) - 1) - self._cooldown_start_bars

        if bars_elapsed >= self.bars:
            self._cooldown_start = None
            self._cooldown_start_bars = None
            self._streak = 0

            return False

        return True
