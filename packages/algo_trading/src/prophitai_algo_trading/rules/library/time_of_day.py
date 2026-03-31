"""Time of day rule — restrict trading to a time window, optionally force-exit by cutoff."""

from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class TimeOfDayRule(TradingRule):
    """Block entries outside an allowed time window and optionally
    force-exit all positions by a cutoff time.

    Args:
        entry_start: Earliest time to allow entries (e.g., time(9, 45)).
        entry_end: Latest time to allow entries (e.g., time(15, 30)).
        exit_by: Force-exit all positions at or after this time.
                 None to disable forced exits.
    """

    def __init__(
        self,
        entry_start: time = time(9, 30),
        entry_end: time = time(15, 30),
        exit_by: time | None = None,
    ):
        self.entry_start = entry_start
        self.entry_end = entry_end
        self.exit_by = exit_by

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        current_time = timestamp.time()
        return not (self.entry_start <= current_time <= self.entry_end)

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        if self.exit_by is None:
            return False
        return timestamp.time() >= self.exit_by
