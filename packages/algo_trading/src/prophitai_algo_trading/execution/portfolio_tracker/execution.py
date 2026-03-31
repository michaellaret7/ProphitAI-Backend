"""Portfolio tracker trade-execution helpers."""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.models import Direction, PositionState, Trade


class PortfolioTrackerExecutionMixin:
    """Trade-execution helpers."""

    def execute_instruction(self, instruction: dict, symbol: str) -> None:
        """Route a trade instruction from PositionTracker to the right method."""
        reason = instruction["reason"]
        price = instruction["price"]
        timestamp = instruction["timestamp"]
        target_shares = instruction.get("target_shares")
        if reason == "open_long":
            self.open_long(symbol, price, timestamp, shares=target_shares)
        elif reason == "close_long":
            self.close_position(symbol, price, timestamp)
        elif reason == "open_short":
            self.open_short(symbol, price, timestamp, shares=target_shares)
        elif reason == "close_short":
            self.close_position(symbol, price, timestamp)
        else:
            raise ValueError(f"Unknown trade reason: {reason}")

    def open_long(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        shares: float | None = None,
    ) -> None:
        """Open a long position using an explicit share target or the injected sizer."""
        context = self.build_portfolio_context(prices={symbol: price}, timestamp=timestamp)
        shares = (
            shares
            if shares is not None
            else self._sizer.calculate_shares(symbol, price, context)
        )
        if pd.isna(shares) or shares <= 0:
            return
        commission = self._cost_model.cost_for_trade(price, shares)
        if self._broker:
            self._broker.buy(symbol, qty=shares)
            print(f"[OPEN LONG] {symbol}  shares={shares}  price={price:.2f}")
        self._latest_prices[symbol] = price
        self.cash -= shares * price + commission
        self._positions[symbol] = PositionState(
            symbol=symbol,
            shares=shares,
            direction=Direction.LONG,
            entry_price=price,
            entry_date=timestamp,
            entry_commission=commission,
        )

    def open_short(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
        shares: float | None = None,
    ) -> None:
        """Open a short position using an explicit share target or the injected sizer."""
        context = self.build_portfolio_context(prices={symbol: price}, timestamp=timestamp)
        raw_shares = (
            shares
            if shares is not None
            else self._sizer.calculate_shares(symbol, price, context)
        )
        shares = math.floor(raw_shares)
        if shares < 1:
            return
        commission = self._cost_model.cost_for_trade(price, shares)
        if self._broker:
            self._broker.sell(symbol, qty=shares)
            print(f"[OPEN SHORT] {symbol}  shares={shares}  price={price:.2f}")
        self._latest_prices[symbol] = price
        self.cash -= commission
        self._positions[symbol] = PositionState(
            symbol=symbol,
            shares=shares,
            direction=Direction.SHORT,
            entry_price=price,
            entry_date=timestamp,
            entry_commission=commission,
        )

    def close_position(self, symbol: str, price: float, timestamp: datetime) -> None:
        """Close a position and log the trade."""
        pos = self._positions.get(symbol)
        if pos is None:
            return

        if self._broker:
            self._broker.close_position(symbol)
            print(f"[CLOSE] {symbol}  price={price:.2f}  direction={pos.direction.value}")

        self._latest_prices[symbol] = price
        exit_commission = self._cost_model.cost_for_trade(price, pos.shares)
        total_commission = pos.entry_commission + exit_commission

        if pos.direction == Direction.LONG:
            self.cash += pos.shares * price - exit_commission
            pnl = (price - pos.entry_price) * pos.shares - total_commission
        else:
            pnl = (pos.entry_price - price) * pos.shares - total_commission
            self.cash += pnl + pos.entry_commission

        entry_value = pos.shares * pos.entry_price
        return_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0.0

        self._trades.append(
            Trade(
                symbol=symbol,
                entry_date=pos.entry_date,
                exit_date=timestamp,
                direction=pos.direction,
                entry_price=pos.entry_price,
                exit_price=price,
                shares=pos.shares,
                pnl=round(pnl, 2),
                return_pct=round(return_pct, 2),
            )
        )
        del self._positions[symbol]
