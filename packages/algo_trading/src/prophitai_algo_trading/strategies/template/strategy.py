"""Concrete scaffold strategy built on the composable base."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_algo_trading.strategies.template.config import TemplateStrategyConfig
from prophitai_algo_trading.strategies.template.indicators import TemplateIndicatorSuite
from prophitai_algo_trading.strategies.template.signals import TemplateSignalModel


class TemplateStrategy(BaseComposableStrategy):
    """Minimal but runnable strategy scaffold for agent-authored variants.

    This class is intentionally generic. The downstream agent should primarily
    customize:
    - the config values in ``TemplateStrategyConfig``
    - indicator composition in ``indicators/suite.py``
    - derived features in ``indicators/custom.py``
    - entry/exit logic in ``signals/model.py``
    """

    def __init__(self, config: TemplateStrategyConfig | None = None) -> None:
        self.config = config or TemplateStrategyConfig()
        super().__init__(
            indicator_suite=TemplateIndicatorSuite(config=self.config),
            signal_model=TemplateSignalModel(
                rsi_long_entry_threshold=self.config.rsi_long_entry_threshold,
                rsi_short_entry_threshold=self.config.rsi_short_entry_threshold,
                allow_shorts=self.config.allow_shorts,
            ),
        )

    @property
    def min_bars_required(self) -> int:
        """Declare the warmup required by the scaffold indicators."""
        return max(
            self.config.fast_ema_period,
            self.config.slow_ema_period,
            self.config.rsi_period,
            self.config.bb_window,
        )

    def get_sizing_hints(
        self,
        row: pd.Series,
        target_position: int,
    ) -> dict[str, object]:
        """Publish a few generic sizing hints from the scaffold features."""
        hints = super().get_sizing_hints(row, target_position)
        trend_gap = row.get("trend_gap")
        if trend_gap is not None and not pd.isna(trend_gap):
            hints["conviction"] = abs(float(trend_gap)) * 100.0
        hints["expected_holding_bars"] = max(3, self.config.fast_ema_period // 2)
        return hints
