"""Stop-loss exit control — force exit when price moves against position."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.risk.base import RiskControl

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class StopLossExitControl(RiskControl):
    """Force exit when price moves against the position by a percentage.

    Direction-aware: triggers when a long drops below entry or a short
    rises above entry by more than ``pct``. Reads position state from
    the portfolio tracker.

    Args:
        pct: Maximum allowed loss as a decimal (e.g., 0.02 = 2%).
    """

    def __init__(self, pct: float):
        self.pct = pct

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return False

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        pos = portfolio.get_position(ticker)
        if pos is None:
            return False
        if pos.direction == Direction.LONG:
            return price <= pos.entry_price * (1 - self.pct)
        return price >= pos.entry_price * (1 + self.pct)
