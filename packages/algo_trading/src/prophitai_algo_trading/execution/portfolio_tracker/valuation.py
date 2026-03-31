"""Portfolio tracker valuation helpers."""

from __future__ import annotations

from datetime import datetime

from prophitai_algo_trading.execution.models import (
    Direction,
    PortfolioContext,
    PositionState,
)


class PortfolioTrackerValuationMixin:
    """Valuation and portfolio-state helpers."""

    def _mark_to_market(self, prices: dict[str, float] | None = None) -> float:
        """Compute total position value at current market prices."""
        position_value = 0.0
        for sym, pos in self._positions.items():
            current_price = (prices or {}).get(
                sym,
                self._latest_prices.get(sym, pos.entry_price),
            )
            if pos.direction == Direction.LONG:
                position_value += pos.shares * current_price
            else:
                position_value += pos.shares * (pos.entry_price - current_price)
        return position_value

    def _compute_exposures(
        self,
        prices: dict[str, float] | None = None,
    ) -> tuple[float, float, float, float]:
        """Return long, short, gross, and net exposure using live prices."""
        long_exposure = 0.0
        short_exposure = 0.0
        for sym, pos in self._positions.items():
            current_price = (prices or {}).get(
                sym,
                self._latest_prices.get(sym, pos.entry_price),
            )
            notional = pos.shares * current_price
            if pos.direction == Direction.LONG:
                long_exposure += notional
            else:
                short_exposure += notional
        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        return long_exposure, short_exposure, gross_exposure, net_exposure

    def build_portfolio_context(
        self,
        prices: dict[str, float] | None = None,
        timestamp: datetime | None = None,
    ) -> PortfolioContext:
        """Build a PortfolioContext snapshot for sizing and risk checks."""
        position_value = self._mark_to_market(prices)
        equity = self.cash + position_value
        self._peak_equity = max(self._peak_equity, equity)
        exposures = self._compute_exposures(prices)
        return PortfolioContext(
            equity=equity,
            cash=self.cash,
            positions=dict(self._positions),
            latest_prices={**self._latest_prices, **(prices or {})},
            open_position_count=len(self._positions),
            gross_exposure=exposures[2],
            net_exposure=exposures[3],
            long_exposure=exposures[0],
            short_exposure=exposures[1],
            peak_equity=self._peak_equity,
            drawdown_pct=(
                max(self._peak_equity - equity, 0.0) / self._peak_equity
                if self._peak_equity > 0
                else 0.0
            ),
            timestamp=timestamp,
        )

    def get_position(self, symbol: str) -> PositionState | None:
        """Return the open position for a symbol, or None if flat."""
        return self._positions.get(symbol)

    def update_market_prices(self, prices: dict[str, float]) -> None:
        """Merge the latest known market prices into the tracker state."""
        self._latest_prices.update(prices)

    @property
    def open_position_count(self) -> int:
        """Number of currently open positions."""
        return len(self._positions)

    @property
    def has_open_positions(self) -> bool:
        """Whether any positions are currently open."""
        return bool(self._positions)

    @property
    def open_symbols(self) -> list[str]:
        """Symbols with currently open positions."""
        return list(self._positions.keys())

    @property
    def last_trade_pnl(self) -> float:
        """P&L of the most recent closed trade, or 0.0 if no trades yet."""
        return self._trades[-1].pnl if self._trades else 0.0

    def get_total_equity(self, prices: dict[str, float] | None = None) -> float:
        """Current total equity (cash plus position value)."""
        return self.cash + self._mark_to_market(prices)
