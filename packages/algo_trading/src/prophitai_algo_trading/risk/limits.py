"""Portfolio-level risk limits: daily loss limit and drawdown limit."""

from __future__ import annotations

from prophitai_algo_trading.risk.base import RiskContext, RiskRule


class DailyLossLimit(RiskRule):
    """Block all entries once today's realized P&L loss exceeds ``loss_pct`` of equity.

    Resets at UTC midnight. Reads the start-of-day equity from the first
    bar seen each day.

    Args:
        loss_pct: Max intraday drawdown as a fraction of equity (0.02 = 2%).
    """

    def __init__(self, loss_pct: float):
        if loss_pct <= 0:
            raise ValueError("loss_pct must be > 0.")

        self.loss_pct = loss_pct
        self._day: object | None = None
        self._day_start_equity: float | None = None

    def _refresh(self, ctx: RiskContext) -> None:
        current_day = ctx.timestamp.date() if hasattr(ctx.timestamp, "date") else None

        if current_day != self._day:
            self._day = current_day
            self._day_start_equity = ctx.portfolio_equity

    def block_entry(self, ctx: RiskContext) -> bool:
        self._refresh(ctx)

        if self._day_start_equity is None or self._day_start_equity <= 0:
            return False

        loss_fraction = (self._day_start_equity - ctx.portfolio_equity) / self._day_start_equity

        return loss_fraction >= self.loss_pct

    def on_bar(self, ctx: RiskContext) -> None:
        self._refresh(ctx)


class PortfolioDrawdownLimit(RiskRule):
    """Block all entries once portfolio drawdown from peak exceeds ``dd_pct``.

    Args:
        dd_pct: Max drawdown from the running peak (0.10 = 10%).
    """

    def __init__(self, dd_pct: float):
        if dd_pct <= 0:
            raise ValueError("dd_pct must be > 0.")

        self.dd_pct = dd_pct

    def block_entry(self, ctx: RiskContext) -> bool:
        if ctx.portfolio_peak <= 0:
            return False

        drawdown = (ctx.portfolio_peak - ctx.portfolio_equity) / ctx.portfolio_peak

        return drawdown >= self.dd_pct
