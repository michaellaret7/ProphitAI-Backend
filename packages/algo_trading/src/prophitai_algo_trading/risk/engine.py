"""Risk engine — coordinates evaluation of risk controls per bar.

Used by EventDrivenBacktestEngine and LiveRunner to check risk controls before
executing trades. Provides a clean interface for entry gating, forced exits,
and lifecycle notifications.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.risk.base import (
    RISK_CANDIDATE_SCORE_ATTR,
    RISK_CANDIDATE_TARGET_ATTR,
    RiskControl,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class RiskEngine:
    """Evaluates a list of RiskControls against each bar.

    Args:
        risk_controls: List of RiskControl instances to evaluate.
    """

    def __init__(self, risk_controls: list[RiskControl]):
        self._risk_controls = risk_controls

    @property
    def active(self) -> bool:
        """Whether any risk controls are configured."""
        return bool(self._risk_controls)

    def allows_entry(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
        target: int | None = None,
        score: float | None = None,
    ) -> bool:
        """Return True if entry is allowed (no risk control blocks it).

        Args:
            ticker: Symbol being evaluated for entry.
            price: Current bar close price.
            timestamp: Bar timestamp.
            df: Full DataFrame with indicators for this ticker.
            portfolio: Shared portfolio tracker.
            target: Intended target position (1 or -1) for this entry check.
            score: Strategy-provided entry score for this candidate.
        """
        previous_target = df.attrs.get(RISK_CANDIDATE_TARGET_ATTR)
        previous_score = df.attrs.get(RISK_CANDIDATE_SCORE_ATTR)
        had_target = RISK_CANDIDATE_TARGET_ATTR in df.attrs
        had_score = RISK_CANDIDATE_SCORE_ATTR in df.attrs

        if target is not None:
            df.attrs[RISK_CANDIDATE_TARGET_ATTR] = target
        if score is not None:
            df.attrs[RISK_CANDIDATE_SCORE_ATTR] = score

        try:
            return not any(
                risk_control.should_block_entry(ticker, price, timestamp, df, portfolio)
                for risk_control in self._risk_controls
            )
        finally:
            if had_target:
                df.attrs[RISK_CANDIDATE_TARGET_ATTR] = previous_target
            else:
                df.attrs.pop(RISK_CANDIDATE_TARGET_ATTR, None)

            if had_score:
                df.attrs[RISK_CANDIDATE_SCORE_ATTR] = previous_score
            else:
                df.attrs.pop(RISK_CANDIDATE_SCORE_ATTR, None)

    def requires_exit(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        """Return True if any risk control forces an exit for this ticker.

        Args:
            ticker: Symbol with an open position.
            price: Current bar close price.
            timestamp: Bar timestamp.
            df: Full DataFrame with indicators for this ticker.
            portfolio: Shared portfolio tracker.
        """
        return any(
            risk_control.should_force_exit(ticker, price, timestamp, df, portfolio)
            for risk_control in self._risk_controls
        )

    def notify_entry(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        """Notify all risk controls that a position was opened."""
        for risk_control in self._risk_controls:
            risk_control.on_entry(ticker, price, timestamp, direction)

    def notify_exit(
        self, ticker: str, price: float, timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        """Notify all risk controls that a position was closed."""
        for risk_control in self._risk_controls:
            risk_control.on_exit(ticker, price, timestamp, direction)

    def notify_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        """Notify all risk controls of a new bar for state updates."""
        for risk_control in self._risk_controls:
            risk_control.on_bar(ticker, price, timestamp)
