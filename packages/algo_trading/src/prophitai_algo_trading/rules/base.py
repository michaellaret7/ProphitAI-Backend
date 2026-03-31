"""Base class for all trading rules.

Trading rules are execution-layer guards evaluated bar-by-bar. They sit
between signal generation and trade execution, governing how trades happen
(cooldowns, stop losses, position limits) rather than what signals fire.

Rules are passed to BacktestEngine and LiveRunner via the ``rules`` parameter
and evaluated by RuleEngine during the bar loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class TradingRule(ABC):
    """Abstract base for all trading rules.

    Rules can block entry signals and force position exits. They receive
    the full bar context (DataFrame, ticker, price, portfolio state) and
    maintain their own per-ticker state across bars via lifecycle hooks.

    Subclasses must implement:
        - should_block_entry: Return True to veto an entry signal.
        - should_force_exit: Return True to force-close a position.

    Optional hooks for state management:
        - on_entry: Called after a position opens.
        - on_exit: Called after a position closes.
        - on_bar: Called every bar for every active ticker.
    """

    @abstractmethod
    def should_block_entry(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        """Return True to veto an entry signal for this ticker.

        Args:
            ticker: Symbol being evaluated.
            price: Current bar close price.
            timestamp: Bar timestamp.
            df: Full DataFrame with indicators for this ticker.
            portfolio: Shared portfolio tracker for portfolio-level checks.
        """

    @abstractmethod
    def should_force_exit(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        """Return True to force-close the position for this ticker.

        Args:
            ticker: Symbol being evaluated.
            price: Current bar close price.
            timestamp: Bar timestamp.
            df: Full DataFrame with indicators for this ticker.
            portfolio: Shared portfolio tracker for portfolio-level checks.
        """

    def on_entry(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        """Hook called after a position is opened. Override to update state.

        Args:
            ticker: Symbol that was entered.
            price: Entry price.
            timestamp: Bar timestamp.
            direction: Position direction (LONG or SHORT).
        """

    def on_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        """Hook called after a position is closed. Override to update state.

        Args:
            ticker: Symbol that was exited.
            price: Exit price.
            timestamp: Bar timestamp.
            direction: Position direction that was closed (LONG or SHORT).
        """

    def on_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Hook called every bar for active tickers. Override to update state."""
