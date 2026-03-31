"""Max daily loss rule — shut down trading when daily loss limit is hit."""

from __future__ import annotations

from datetime import datetime, date
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class MaxDailyLossRule(TradingRule):
    """Force-exit all positions and block entries when the portfolio is
    down more than ``max_pct`` from the day's starting equity.

    Resets at the start of each new trading day. Captures start-of-day
    equity on the first check of each calendar date.

    Args:
        max_pct: Maximum allowed daily loss as a decimal (e.g., 0.02 = 2%).
    """

    def __init__(self, max_pct: float):
        self.max_pct = max_pct
        self._current_date: date | None = None
        self._sod_equity: float = 0.0

    # ================================
    # --> Helper funcs
    # ================================

    def _check_daily_loss(
        self, ticker: str, price: float, timestamp: datetime,
        portfolio: PortfolioTracker,
    ) -> bool:
        """Return True if daily loss threshold is breached."""
        bar_date = timestamp.date()

        # Reason: capture start-of-day equity on the first check of each new date
        if self._current_date != bar_date:
            self._current_date = bar_date
            self._sod_equity = portfolio.get_total_equity()

        if self._sod_equity <= 0:
            return False

        current_equity = portfolio.get_total_equity()
        daily_return = (current_equity - self._sod_equity) / self._sod_equity
        return daily_return <= -self.max_pct

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return self._check_daily_loss(ticker, price, timestamp, portfolio)

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return self._check_daily_loss(ticker, price, timestamp, portfolio)
