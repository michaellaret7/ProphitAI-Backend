"""Portfolio accounting for the event-driven engine.

Tracks cash, open positions, completed trades, and equity history. Consumes
target positions (-1, 0, 1) and share counts from a sizer. Supports long
and short.

This is the full replacement for the old PortfolioTracker + PositionTracker
+ execution/hydration/reporting/valuation mixins. Flat, explicit, ~180 LOC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.portfolio.cost_model import CostModel


#     ================================
# --> Helper funcs
#     ================================

def _format_entry_alphas(
    entry_alphas: tuple[tuple[str, float], ...] | None,
) -> str:
    """Render entry-alpha attribution as a CSV-friendly string.

    Format: ``"name:weight,name:weight"`` with weights to 4 decimals.
    Empty/None → ``""``.
    """
    if not entry_alphas:
        return ""

    return ",".join(f"{name}:{weight:.4f}" for name, weight in entry_alphas)


@dataclass
class Position:
    """Open position state."""

    symbol: str
    shares: float
    direction: int
    entry_price: float
    entry_time: datetime
    entry_cost: float
    entry_alphas: tuple[tuple[str, float], ...] | None = None


@dataclass
class Trade:
    """Completed round-trip trade."""

    symbol: str
    direction: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    return_pct: float
    entry_alphas: tuple[tuple[str, float], ...] | None = None
    exit_reason: str | None = None


class Portfolio:
    """Long/short portfolio with cost-aware accounting.

    Args:
        initial_capital: Starting cash.
        cost_model: Transaction cost model (default: zero cost).
    """

    def __init__(self, initial_capital: float, cost_model: CostModel | None = None):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.cost_model = cost_model or CostModel()
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self._equity_history: list[dict] = []
        self._latest_prices: dict[str, float] = {}

    @property
    def latest_prices(self) -> dict[str, float]:
        """Read-only view of the last-known price per symbol."""
        return dict(self._latest_prices)

    def get_position(self, symbol: str) -> int:
        """Current position state: 1 (long), -1 (short), 0 (flat)."""
        pos = self.positions.get(symbol)
        return pos.direction if pos else 0

    def equity(self, prices: dict[str, float] | None = None) -> float:
        """Mark-to-market equity.

        Long positions: cash + sum(shares * price).
        Short positions: cash + sum(shares * (entry - price)) — shorts are booked
        against entry proceeds without reserving cash; their P&L is the delta.
        """
        marks = prices if prices is not None else self._latest_prices
        total = self.cash

        for symbol, pos in self.positions.items():
            mark = marks.get(symbol, pos.entry_price)

            if pos.direction == 1:
                total += pos.shares * mark
            else:
                total += pos.shares * (pos.entry_price - mark)

        return total

    def open(
        self,
        symbol: str,
        direction: int,
        shares: float,
        price: float,
        timestamp: datetime,
        entry_alphas: tuple[tuple[str, float], ...] | None = None,
    ) -> bool:
        """Open a new position. Returns True on success, False if rejected.

        Rejects if already holding a position in ``symbol``, or if the trade
        would take cash negative (long only — shorts don't reserve cash here).
        """
        if direction not in (1, -1):
            raise ValueError(f"direction must be 1 or -1, got {direction}")

        if symbol in self.positions:
            return False

        if shares <= 0:
            return False

        cost = self.cost_model.cost(price, shares)

        if direction == 1:
            outlay = shares * price + cost

            if outlay > self.cash:
                return False

            self.cash -= outlay
        else:
            self.cash -= cost

        self.positions[symbol] = Position(
            symbol=symbol,
            shares=shares,
            direction=direction,
            entry_price=price,
            entry_time=timestamp,
            entry_cost=cost,
            entry_alphas=entry_alphas,
        )
        self._latest_prices[symbol] = price

        return True

    def close(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        exit_reason: str | None = None,
    ) -> Trade | None:
        """Close a position. Returns the Trade record, or None if no position."""
        pos = self.positions.pop(symbol, None)

        if pos is None:
            return None

        exit_cost = self.cost_model.cost(price, pos.shares)
        total_cost = pos.entry_cost + exit_cost

        if pos.direction == 1:
            self.cash += pos.shares * price - exit_cost
            pnl = (price - pos.entry_price) * pos.shares - total_cost
        else:
            pnl = (pos.entry_price - price) * pos.shares - total_cost
            self.cash += pnl + pos.entry_cost

        notional = pos.shares * pos.entry_price
        return_pct = (pnl / notional) * 100.0 if notional > 0 else 0.0

        trade = Trade(
            symbol=symbol,
            direction=pos.direction,
            entry_time=pos.entry_time,
            exit_time=timestamp,
            entry_price=pos.entry_price,
            exit_price=price,
            shares=pos.shares,
            pnl=pnl,
            return_pct=return_pct,
            entry_alphas=pos.entry_alphas,
            exit_reason=exit_reason,
        )

        self.trades.append(trade)
        self._latest_prices[symbol] = price

        return trade

    def mark(self, prices: dict[str, float]) -> None:
        """Update last-known prices for mark-to-market equity."""
        self._latest_prices.update(prices)

    def record_equity(self, timestamp: datetime, prices: dict[str, float]) -> None:
        """Snapshot equity at this bar."""
        self.mark(prices)

        self._equity_history.append({
            "timestamp": timestamp,
            "equity": self.equity(prices),
            "cash": self.cash,
            "positions": len(self.positions),
        })

    def equity_curve(self) -> pd.DataFrame:
        """Equity history as a DataFrame indexed by timestamp."""
        if not self._equity_history:
            return pd.DataFrame(columns=["equity", "cash", "positions"])

        df = pd.DataFrame(self._equity_history).set_index("timestamp").sort_index()

        return df[~df.index.duplicated(keep="last")]

    def trades_df(self) -> pd.DataFrame:
        """Trade log as a DataFrame."""
        columns = [
            "symbol", "direction", "entry_time", "exit_time",
            "entry_price", "exit_price", "shares", "pnl", "return_pct",
            "entry_alphas", "exit_reason",
        ]

        if not self.trades:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame([
            {
                "symbol": t.symbol,
                "direction": "long" if t.direction == 1 else "short",
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "shares": t.shares,
                "pnl": t.pnl,
                "return_pct": t.return_pct,
                "entry_alphas": _format_entry_alphas(t.entry_alphas),
                "exit_reason": t.exit_reason or "",
            }
            for t in self.trades
        ])
