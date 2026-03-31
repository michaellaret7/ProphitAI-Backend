"""Indicator suite for the strategy scaffold."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from prophitai_algo_trading.indicators import BaseIndicatorSuite, IndicatorSpec
from prophitai_algo_trading.strategies.template.config import TemplateStrategyConfig
from prophitai_algo_trading.strategies.template.indicators.custom import (
    add_template_indicator_features,
)


class TemplateIndicatorSuite(BaseIndicatorSuite):
    """Compose a small, editable indicator pipeline for the scaffold."""

    def __init__(self, config: TemplateStrategyConfig):
        self.config = config
        super().__init__()

    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        """Return the shared indicators used by the scaffold."""
        return (
            IndicatorSpec(
                indicator="ema",
                params={
                    "span": self.config.fast_ema_period,
                    "output_column": "ema_fast",
                },
                description="Fast trend EMA.",
            ),
            IndicatorSpec(
                indicator="ema",
                params={
                    "span": self.config.slow_ema_period,
                    "output_column": "ema_slow",
                },
                description="Slow trend EMA.",
            ),
            IndicatorSpec(
                indicator="rsi",
                params={"period": self.config.rsi_period},
                description="Momentum confirmation oscillator.",
            ),
        )

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate the indicator pipeline and add derived features."""
        calculated = super().calculate(df)
        return add_template_indicator_features(calculated)

    def update_last_row(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicators and refresh derived features."""
        updated = super().update_last_row(df)
        return add_template_indicator_features(updated)
