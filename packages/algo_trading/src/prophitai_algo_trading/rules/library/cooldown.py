"""Cooldown rule — block re-entry for N bars after exiting a position."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class CooldownRule(TradingRule):
    """Block re-entry for N bars after exiting a position on a ticker.

    Direction-neutral: applies equally to longs and shorts. Tracks
    per-ticker bar counts and last exit bar.

    Args:
        bars: Minimum number of bars to wait after an exit before
              allowing a new entry on the same ticker.
    """

    def __init__(self, bars: int):
        self.bars = bars
        self._last_exit_bar: dict[str, int] = {}
        self._bar_count: dict[str, int] = {}

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        """Block entry if cooldown period has not elapsed."""
        if ticker not in self._last_exit_bar:
            return False
        bars_since_exit = self._bar_count.get(ticker, 0) - self._last_exit_bar[ticker]
        return bars_since_exit < self.bars

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return False

    def on_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._last_exit_bar[ticker] = self._bar_count.get(ticker, 0)

    def on_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        self._bar_count[ticker] = self._bar_count.get(ticker, 0) + 1
