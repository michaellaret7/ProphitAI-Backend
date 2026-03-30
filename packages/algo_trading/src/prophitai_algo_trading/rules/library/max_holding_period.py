"""Max holding period rule — force exit after holding for N bars."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class MaxHoldingPeriodRule(TradingRule):
    """Force exit after holding a position for N bars.

    Direction-neutral: applies equally to long and short positions.
    Prevents capital from being tied up in stale positions that
    aren't hitting stop loss or take profit.

    Args:
        bars: Maximum number of bars to hold a position.
    """

    def __init__(self, bars: int):
        self.bars = bars
        self._entry_bar: dict[str, int] = {}
        self._bar_count: dict[str, int] = {}

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return False

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        if ticker not in self._entry_bar:
            return False
        bars_held = self._bar_count.get(ticker, 0) - self._entry_bar[ticker]
        return bars_held >= self.bars

    def on_entry(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._entry_bar[ticker] = self._bar_count.get(ticker, 0)

    def on_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._entry_bar.pop(ticker, None)

    def on_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        self._bar_count[ticker] = self._bar_count.get(ticker, 0) + 1
