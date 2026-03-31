"""Portfolio tracker hydration helpers."""

from __future__ import annotations

from datetime import datetime

from prophitai_algo_trading.execution.models import Direction, PositionState


class PortfolioTrackerHydrationMixin:
    """Live-startup hydration helpers."""

    def seed_cash(self, cash: float) -> None:
        """Override cash with the broker's reported cash balance."""
        self.cash = cash

    def seed_position(
        self,
        symbol: str,
        shares: float,
        direction: Direction,
        entry_price: float,
        entry_date: datetime | None,
        entry_commission: float = 0.0,
    ) -> None:
        """Inject a broker position without executing a trade."""
        self._positions[symbol] = PositionState(
            symbol=symbol,
            shares=shares,
            direction=direction,
            entry_price=entry_price,
            entry_date=entry_date,
            entry_commission=entry_commission,
        )

    def seed_latest_prices(self, prices: dict[str, float]) -> None:
        """Bulk-set latest prices from warmup data."""
        self._latest_prices.update(prices)
