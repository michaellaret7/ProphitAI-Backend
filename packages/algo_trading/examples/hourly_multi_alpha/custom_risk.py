"""Custom risk rules for the hourly multi-alpha example."""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.core.models import AlgorithmContext, PortfolioTarget
from prophitai_algo_trading.risk import RiskContext, RiskRule


class IntradayDrawdownKillSwitch:
    """Flatten and block entries after a same-day portfolio drawdown breach."""

    def __init__(self, loss_pct: float = 0.03):
        if loss_pct <= 0.0:
            raise ValueError("loss_pct must be > 0")

        self._loss_pct = loss_pct
        self._current_day = None
        self._day_start_equity: float | None = None
        self._halted = False

    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        day = ctx.timestamp.date()
        equity = ctx.portfolio.equity()

        if day != self._current_day:
            self._current_day = day
            self._day_start_equity = equity
            self._halted = False

        if self._day_start_equity is None or self._day_start_equity <= 0.0:
            return list(targets)

        drawdown = (equity - self._day_start_equity) / self._day_start_equity

        if drawdown <= -self._loss_pct:
            self._halted = True

        if not self._halted:
            return list(targets)

        return [
            PortfolioTarget(
                symbol=symbol,
                target_shares=0.0,
                exit_reason="intraday_drawdown_kill_switch",
            )
            for symbol in ctx.portfolio.positions
        ]


class PositionAgeExit(RiskRule):
    """Force exit positions that have stayed open too long."""

    def __init__(
        self,
        max_bars: int = 70,
        max_duration: timedelta = timedelta(days=14),
    ):
        if max_bars <= 0:
            raise ValueError("max_bars must be > 0")

        super().__init__()
        self._max_bars = max_bars
        self._max_duration = max_duration
        self._entry_bars: dict[str, int] = {}

    def on_entry(self, ctx: RiskContext) -> None:
        self._entry_bars[ctx.symbol] = len(ctx.df) - 1

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        self._entry_bars.pop(ctx.symbol, None)

    def force_exit(self, ctx: RiskContext) -> bool:
        if ctx.current_position == 0:
            return False

        entry_bar = self._entry_bars.get(ctx.symbol)

        if entry_bar is not None and (len(ctx.df) - 1) - entry_bar >= self._max_bars:
            return True

        if ctx.entry_time is not None:
            return ctx.timestamp - ctx.entry_time >= self._max_duration

        return False
