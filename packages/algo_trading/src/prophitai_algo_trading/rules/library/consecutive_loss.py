"""Consecutive loss rule — pause trading after N consecutive losing trades."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class ConsecutiveLossRule(TradingRule):
    """Block entries after N consecutive losing trades, pause for M bars.

    Direction-aware: determines win/loss based on position direction.
    For longs, a loss is exit_price < entry_price. For shorts, a loss
    is exit_price > entry_price. Counter resets after a winning trade
    or after the pause period elapses. A ``pause_bars`` value of 0
    disables the cooldown and resets the streak immediately.

    Args:
        max_losses: Consecutive losses before blocking entries.
        pause_bars: Number of bars to pause after hitting the loss limit.
                    Defaults to 0 (disable the cooldown and reset immediately).
    """

    def __init__(self, max_losses: int, pause_bars: int = 0):
        self.max_losses = max_losses
        self.pause_bars = pause_bars
        self._consecutive_losses: int = 0
        self._entry_prices: dict[str, float] = {}
        self._pause_until_bar: int = 0
        self._global_bar_count: int = 0
        self._last_bar_timestamp: datetime | None = None

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        if self._consecutive_losses >= self.max_losses:
            if self.pause_bars <= 0:
                self._consecutive_losses = 0
                self._pause_until_bar = 0
                return False
            if self._global_bar_count >= self._pause_until_bar:
                # Reason: pause period elapsed, reset and allow trading
                self._consecutive_losses = 0
                self._pause_until_bar = 0
                return False
            return True
        return False

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return False

    def on_entry(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._entry_prices[ticker] = price

    def on_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        entry_price = self._entry_prices.pop(ticker, price)

        if direction == Direction.LONG:
            is_loss = price < entry_price
        else:
            is_loss = price > entry_price

        if is_loss:
            self._consecutive_losses += 1
            if self._consecutive_losses >= self.max_losses and self.pause_bars > 0:
                self._pause_until_bar = self._global_bar_count + self.pause_bars
        else:
            self._consecutive_losses = 0

    def on_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        if self._last_bar_timestamp != timestamp:
            self._global_bar_count += 1
            self._last_bar_timestamp = timestamp
