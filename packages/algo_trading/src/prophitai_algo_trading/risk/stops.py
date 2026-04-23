"""Exit rules: stop loss, trailing stop, time stop, profit target."""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.risk.base import RiskContext, RiskRule


class StopLossExit(RiskRule):
    """Force exit when the price moves against the position by ``pct`` percent.

    Args:
        pct: Loss threshold as a fraction (0.05 = 5% adverse move).
    """

    def __init__(self, pct: float):
        self.pct = pct

    def force_exit(self, ctx: RiskContext) -> bool:
        if ctx.current_position == 0 or ctx.entry_price is None:
            return False

        if ctx.current_position == 1:
            return ctx.price <= ctx.entry_price * (1.0 - self.pct)

        return ctx.price >= ctx.entry_price * (1.0 + self.pct)


class TrailingStopExit(RiskRule):
    """Force exit when the price retraces ``pct`` from its favorable extreme.

    Tracks the best price since entry on a per-symbol basis.

    Args:
        pct: Retracement threshold as a fraction.
    """

    def __init__(self, pct: float):
        self.pct = pct
        self._extremes: dict[str, float] = {}

    def on_entry(self, ctx: RiskContext) -> None:
        self._extremes[ctx.symbol] = ctx.price

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        self._extremes.pop(ctx.symbol, None)

    def on_bar(self, ctx: RiskContext) -> None:
        if ctx.current_position == 0:
            return

        current = self._extremes.get(ctx.symbol)

        if current is None:
            self._extremes[ctx.symbol] = ctx.price

            return

        if ctx.current_position == 1:
            self._extremes[ctx.symbol] = max(current, ctx.price)
        else:
            self._extremes[ctx.symbol] = min(current, ctx.price)

    def force_exit(self, ctx: RiskContext) -> bool:
        if ctx.current_position == 0:
            return False

        extreme = self._extremes.get(ctx.symbol)

        if extreme is None:
            return False

        if ctx.current_position == 1:
            return ctx.price <= extreme * (1.0 - self.pct)

        return ctx.price >= extreme * (1.0 + self.pct)


class TimeStop(RiskRule):
    """Force exit after holding for more than ``max_bars`` bars or ``max_duration``.

    Only one of ``max_bars`` or ``max_duration`` must be provided.

    Args:
        max_bars: Exit if bars_held > max_bars.
        max_duration: Exit if wall-clock duration > max_duration.
    """

    def __init__(
        self,
        max_bars: int | None = None,
        max_duration: timedelta | None = None,
    ):
        if max_bars is None and max_duration is None:
            raise ValueError("TimeStop requires max_bars or max_duration.")

        self.max_bars = max_bars
        self.max_duration = max_duration
        self._entry_bars: dict[str, int] = {}

    def on_entry(self, ctx: RiskContext) -> None:
        self._entry_bars[ctx.symbol] = len(ctx.df) - 1

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        self._entry_bars.pop(ctx.symbol, None)

    def force_exit(self, ctx: RiskContext) -> bool:
        if ctx.current_position == 0:
            return False

        if self.max_bars is not None:
            entry_bar = self._entry_bars.get(ctx.symbol)

            if entry_bar is not None and (len(ctx.df) - 1) - entry_bar >= self.max_bars:
                return True

        if self.max_duration is not None and ctx.entry_time is not None:
            if ctx.timestamp - ctx.entry_time >= self.max_duration:
                return True

        return False


class ProfitTargetExit(RiskRule):
    """Force exit when price moves favorably by ``pct`` percent.

    Args:
        pct: Profit threshold as a fraction (0.05 = 5% favorable move).
    """

    def __init__(self, pct: float):
        self.pct = pct

    def force_exit(self, ctx: RiskContext) -> bool:
        if ctx.current_position == 0 or ctx.entry_price is None:
            return False

        if ctx.current_position == 1:
            return ctx.price >= ctx.entry_price * (1.0 + self.pct)

        return ctx.price <= ctx.entry_price * (1.0 - self.pct)
