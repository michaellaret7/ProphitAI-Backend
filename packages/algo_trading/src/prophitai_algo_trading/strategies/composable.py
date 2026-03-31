"""Composable strategy base for suite-driven strategies."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.signals.base import BaseSignalModel, SignalDict
from prophitai_algo_trading.strategies.base import BaseStrategy


__all__ = ["BaseComposableStrategy"]


class BaseComposableStrategy(BaseStrategy):
    """Strategy base that delegates to an indicator suite and signal model.

    Concrete strategies still own their parameters, warmup declaration, and any
    optional sizing hints. This base only removes the repeated plumbing needed
    to wire shared indicator and signal infrastructure into the engine-facing
    ``BaseStrategy`` contract.
    """

    def __init__(
        self,
        *,
        indicator_suite: BaseIndicatorSuite,
        signal_model: BaseSignalModel,
    ) -> None:
        self._indicator_suite = indicator_suite
        self._signal_model = signal_model

    @property
    def indicator_suite(self) -> BaseIndicatorSuite:
        """Expose the configured indicator suite for advanced callers/tests."""
        return self._indicator_suite

    @property
    def signal_model(self) -> BaseSignalModel:
        """Expose the configured signal model for advanced callers/tests."""
        return self._signal_model

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate the configured indicator suite on the full frame."""
        if df.empty:
            return df
        return self._indicator_suite.calculate(df)

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Update the configured indicator suite for the last row."""
        if df.empty:
            return df
        return self._indicator_suite.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> SignalDict:
        """Generate the standard 4-way signal dictionary via the signal model."""
        return self._signal_model.generate(df)

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Delegate entry scoring to the configured signal model."""
        return self._signal_model.score_entries(df)
