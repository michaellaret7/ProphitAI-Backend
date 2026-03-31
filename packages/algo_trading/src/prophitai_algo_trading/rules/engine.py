"""Rule engine — coordinates evaluation of trading rules per bar.

Used by BacktestEngine and LiveRunner to check rules before executing
trades. Provides a clean interface for entry gating, forced exits, and
lifecycle notifications.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.rules.base import (
    CANDIDATE_SCORE_ATTR,
    CANDIDATE_TARGET_ATTR,
    TradingRule,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class RuleEngine:
    """Evaluates a list of TradingRules against each bar.

    Args:
        rules: List of TradingRule instances to evaluate.
    """

    def __init__(self, rules: list[TradingRule]):
        self._rules = rules

    @property
    def active(self) -> bool:
        """Whether any rules are configured."""
        return bool(self._rules)

    def check_entry(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
        target: int | None = None,
        score: float | None = None,
    ) -> bool:
        """Return True if entry is ALLOWED (no rule blocks it).

        Args:
            ticker: Symbol being evaluated for entry.
            price: Current bar close price.
            timestamp: Bar timestamp.
            df: Full DataFrame with indicators for this ticker.
            portfolio: Shared portfolio tracker.
            target: Intended target position (1 or -1) for this entry check.
            score: Strategy-provided entry score for this candidate.
        """
        previous_target = df.attrs.get(CANDIDATE_TARGET_ATTR)
        previous_score = df.attrs.get(CANDIDATE_SCORE_ATTR)
        had_target = CANDIDATE_TARGET_ATTR in df.attrs
        had_score = CANDIDATE_SCORE_ATTR in df.attrs

        if target is not None:
            df.attrs[CANDIDATE_TARGET_ATTR] = target
        if score is not None:
            df.attrs[CANDIDATE_SCORE_ATTR] = score

        try:
            return not any(
                rule.should_block_entry(ticker, price, timestamp, df, portfolio)
                for rule in self._rules
            )
        finally:
            if had_target:
                df.attrs[CANDIDATE_TARGET_ATTR] = previous_target
            else:
                df.attrs.pop(CANDIDATE_TARGET_ATTR, None)

            if had_score:
                df.attrs[CANDIDATE_SCORE_ATTR] = previous_score
            else:
                df.attrs.pop(CANDIDATE_SCORE_ATTR, None)

    def check_forced_exit(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        """Return True if ANY rule forces an exit for this ticker.

        Args:
            ticker: Symbol with an open position.
            price: Current bar close price.
            timestamp: Bar timestamp.
            df: Full DataFrame with indicators for this ticker.
            portfolio: Shared portfolio tracker.
        """
        return any(
            rule.should_force_exit(ticker, price, timestamp, df, portfolio)
            for rule in self._rules
        )

    def notify_entry(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        """Notify all rules that a position was opened."""
        for rule in self._rules:
            rule.on_entry(ticker, price, timestamp, direction)

    def notify_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        """Notify all rules that a position was closed."""
        for rule in self._rules:
            rule.on_exit(ticker, price, timestamp, direction)

    def notify_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Notify all rules of a new bar for state updates."""
        for rule in self._rules:
            rule.on_bar(ticker, price, timestamp)
