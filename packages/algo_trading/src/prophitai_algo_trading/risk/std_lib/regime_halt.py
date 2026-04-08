"""Regime-based halt control — blocks entries or forces exits based on market state."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.risk.base import RiskControl

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class RegimeHaltControl(RiskControl):
    """Block entries and optionally force exits based on a regime column.

    A regime column (e.g., ``"market_state_regime"``) must be present in the
    DataFrame, typically produced by a custom indicator upstream in the
    indicator pipeline.

    Args:
        regime_column: Name of the column containing regime labels.
        allowed_long_regimes: Regime values that permit long entries.
            Empty tuple means all regimes are allowed for longs.
        allowed_short_regimes: Regime values that permit short entries.
            Empty tuple means all regimes are allowed for shorts.
        force_exit_on_halt: If ``True``, force-exit existing positions when
            the current regime is not in the allowed set. Default ``True``.
    """

    def __init__(
        self,
        regime_column: str,
        allowed_long_regimes: tuple[str | int, ...] = (),
        allowed_short_regimes: tuple[str | int, ...] = (),
        force_exit_on_halt: bool = True,
    ):
        self.regime_column = regime_column
        self.allowed_long_regimes = allowed_long_regimes
        self.allowed_short_regimes = allowed_short_regimes
        self.force_exit_on_halt = force_exit_on_halt

    # ================================
    # --> Helper funcs
    # ================================

    def _get_regime(self, df: pd.DataFrame) -> str | int | None:
        """Read the current regime value from the latest row."""
        if not self.has_columns(df, self.regime_column):
            return None

        value = self.latest_row(df)[self.regime_column]

        if pd.isna(value):
            return None

        return value

    def _is_blocked(self, regime: str | int | None, direction: Direction) -> bool:
        """Check if the given direction is blocked under the current regime."""
        if regime is None:
            # Reason: missing regime data is treated as blocked to fail safe
            return True

        if direction == Direction.LONG and self.allowed_long_regimes:
            return regime not in self.allowed_long_regimes

        if direction == Direction.SHORT and self.allowed_short_regimes:
            return regime not in self.allowed_short_regimes

        return False

    # ================================
    # --> RiskControl impl
    # ================================

    def should_block_entry(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        regime = self._get_regime(df)

        direction = self.candidate_direction(df)
        if direction is None:
            return True

        return self._is_blocked(regime, direction)

    def should_force_exit(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        if not self.force_exit_on_halt:
            return False

        pos = portfolio.get_position(ticker)
        if pos is None:
            return False

        regime = self._get_regime(df)

        return self._is_blocked(regime, pos.direction)
