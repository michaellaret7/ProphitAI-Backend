"""Portfolio drawdown limit control — shut down trading past a drawdown limit."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.risk.base import RiskControl

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class PortfolioDrawdownLimitControl(RiskControl):
    """Force-exit all positions and block entries when portfolio equity
    drops more than ``max_pct`` from its all-time high.

    Tracks peak equity across the entire run. Once breached, blocks
    all entries and forces all exits until equity recovers.

    Args:
        max_pct: Maximum allowed drawdown as a decimal (e.g., 0.10 = 10%).
    """

    def __init__(self, max_pct: float):
        self.max_pct = max_pct
        self._peak_equity: float = 0.0

    # ================================
    # --> Helper funcs
    # ================================

    def _check_drawdown(
        self, ticker: str, price: float, portfolio: PortfolioTracker,
    ) -> bool:
        """Return True if drawdown from peak exceeds threshold."""
        current_equity = portfolio.get_total_equity()

        if current_equity > self._peak_equity:
            self._peak_equity = current_equity

        if self._peak_equity <= 0:
            return False

        drawdown = (self._peak_equity - current_equity) / self._peak_equity
        return drawdown >= self.max_pct

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return self._check_drawdown(ticker, price, portfolio)

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return self._check_drawdown(ticker, price, portfolio)
