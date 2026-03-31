"""Indicator suite for the strategy scaffold."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from prophitai_algo_trading.indicators import BaseIndicatorSuite, IndicatorSpec
from prophitai_algo_trading.strategies.template.config import TemplateStrategyConfig
from prophitai_algo_trading.strategies.template.indicators.custom import (
    add_template_indicator_features,
)
from prophitai_algo_trading.strategies.template.indicators.custom_indicator import (
    BollingerBandIndicator,
)


class TemplateIndicatorSuite(BaseIndicatorSuite):
    """Compose a small, editable indicator pipeline for the scaffold.

    Shared indicators use string registry keys (``"ema"``, ``"rsi"``).
    Custom indicators use class references (``BollingerBandIndicator``).
    """

    def __init__(self, config: TemplateStrategyConfig):
        self.config = config
        super().__init__()

    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        """Return the ordered indicator specs for the scaffold."""
        return (
            # Reason: shared indicators are referenced by string key.
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
            # Reason: custom indicators are referenced by class.
            IndicatorSpec(
                indicator=BollingerBandIndicator,
                params={
                    "window": self.config.bb_window,
                    "num_std": self.config.bb_num_std,
                },
                description="Custom Bollinger Band indicator.",
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
