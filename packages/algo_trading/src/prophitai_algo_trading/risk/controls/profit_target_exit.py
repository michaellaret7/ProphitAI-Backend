"""Profit-target exit control — force exit when price moves in favor of position."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.risk.base import RiskControl

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class ProfitTargetExitControl(RiskControl):
    """Force exit when price moves in favor of the position by a percentage.

    Direction-aware: for longs, exits when price rises above entry by
    ``pct``. For shorts, exits when price drops below entry by ``pct``.
    Reads position state from the portfolio tracker.

    Args:
        pct: Target profit as a decimal (e.g., 0.05 = 5%).
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
            return price >= pos.entry_price * (1 + self.pct)
        return price <= pos.entry_price * (1 - self.pct)
