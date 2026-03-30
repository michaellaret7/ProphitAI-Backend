"""Trailing stop rule — force exit when price retraces from best price."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class TrailingStopRule(TradingRule):
    """Force exit when price retraces from the best price since entry.

    Direction-aware: for longs, tracks the high-water mark and exits on
    a drop. For shorts, tracks the low-water mark and exits on a rise.
    Reads position direction from the portfolio tracker.

    Args:
        pct: Maximum allowed retracement as a decimal (e.g., 0.05 = 5%).
    """

    def __init__(self, pct: float):
        self.pct = pct
        self._best_price: dict[str, float] = {}

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return False

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        if ticker not in self._best_price:
            return False
        pos = portfolio.get_position(ticker)
        if pos is None:
            return False
        best = self._best_price[ticker]
        if pos.direction == Direction.LONG:
            if price > best:
                self._best_price[ticker] = price
                best = price
            return price <= best * (1 - self.pct)
        # SHORT: track lowest price since entry, exit if price rises above it
        if price < best:
            self._best_price[ticker] = price
            best = price
        return price >= best * (1 + self.pct)

    def on_entry(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._best_price[ticker] = price

    def on_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._best_price.pop(ticker, None)
