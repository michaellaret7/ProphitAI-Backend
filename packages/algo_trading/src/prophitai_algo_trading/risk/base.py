"""Base class for all execution-layer risk controls.

Risk controls are execution-layer guards evaluated bar-by-bar. They sit
between signal generation and trade execution, governing how trades happen
(cooldowns, stop losses, position limits) rather than what signals fire.

Risk controls are passed to EventDrivenBacktestEngine and LiveRunner via the
``risk_controls`` parameter and evaluated by RiskEngine during the bar loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


RISK_CANDIDATE_TARGET_ATTR = "_risk_candidate_target"
RISK_CANDIDATE_SCORE_ATTR = "_risk_candidate_score"


class RiskControl(ABC):
    """Abstract base for all execution-layer risk controls.

    Risk controls can block entry signals and force position exits. They receive
    the full bar context (DataFrame, ticker, price, portfolio state) and
    maintain their own per-ticker state across bars via lifecycle hooks.

    During entry evaluation, RiskEngine annotates ``df.attrs`` with:
        - ``_risk_candidate_target``: Intended target position (1 or -1)
        - ``_risk_candidate_score``: Strategy entry score for that signal

    This lets risk controls express direction-aware or score-aware entry gating
    without changing the public method signature. These attrs are
    ephemeral to the current risk-control evaluation call: risk controls must
    not cache
    ``df`` or persist references to ``df.attrs`` beyond the synchronous
    execution of ``should_block_entry`` / ``should_force_exit``.

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

    # ================================
    # --> Helper funcs
    # ================================

    @staticmethod
    def latest_row(df: pd.DataFrame) -> pd.Series:
        """Return the latest bar/indicator row."""
        return df.iloc[-1]

    @staticmethod
    def has_columns(df: pd.DataFrame, *columns: str) -> bool:
        """Return True if the DataFrame contains all required columns."""
        return all(column in df.columns for column in columns)

    @staticmethod
    def candidate_target(df: pd.DataFrame) -> int:
        """Return the intended target position for the current entry check."""
        return int(df.attrs.get(RISK_CANDIDATE_TARGET_ATTR, 0) or 0)

    @staticmethod
    def candidate_score(df: pd.DataFrame) -> float:
        """Return the strategy-provided entry score for the current signal."""
        return float(df.attrs.get(RISK_CANDIDATE_SCORE_ATTR, 0.0) or 0.0)

    @classmethod
    def candidate_direction(cls, df: pd.DataFrame) -> Direction | None:
        """Return the intended entry direction for the current signal."""
        target = cls.candidate_target(df)
        if target > 0:
            return Direction.LONG
        if target < 0:
            return Direction.SHORT
        return None

    @classmethod
    def candidate_is_long(cls, df: pd.DataFrame) -> bool:
        """Return True if the current entry candidate is long."""
        return cls.candidate_direction(df) == Direction.LONG

    @classmethod
    def candidate_is_short(cls, df: pd.DataFrame) -> bool:
        """Return True if the current entry candidate is short."""
        return cls.candidate_direction(df) == Direction.SHORT
