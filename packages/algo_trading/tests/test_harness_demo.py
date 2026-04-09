"""Demo test file showing the strategy test harness in action.

Builds a minimal SMA crossover strategy inline, wires up a manifest,
and inherits all contract mixins.  Run with:

    pytest packages/algo_trading/tests/test_harness_demo.py -v
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.signals.base import BaseSignalModel
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_algo_trading.testing import (
    ConfigContract,
    IndicatorSuiteContract,
    LeakageContract,
    SignalModelContract,
    StrategyContract,
    StrategyTestManifest,
)


# ================================
# --> Minimal SMA crossover strategy (test-only)
# ================================


@dataclass(frozen=True)
class SmaCrossoverConfig:
    """Config for SMA crossover strategy."""

    fast_period: int = 10
    slow_period: int = 30


class SmaCrossoverSuite(BaseIndicatorSuite):
    """Indicator suite: fast SMA + slow SMA."""

    def __init__(self, config: SmaCrossoverConfig) -> None:
        self._config = config
        super().__init__()

    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        return [
            IndicatorSpec(
                "sma",
                params={
                    "window": self._config.fast_period,
                    "output_column": "sma_fast",
                },
            ),
            IndicatorSpec(
                "sma",
                params={
                    "window": self._config.slow_period,
                    "output_column": "sma_slow",
                },
            ),
        ]


class SmaCrossoverSignalModel(BaseSignalModel):
    """Signal model: long when fast > slow, short when fast < slow."""

    required_columns = ("sma_fast", "sma_slow")

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        fast = df["sma_fast"]
        slow = df["sma_slow"]

        return (fast > slow) & (fast.shift(1) <= slow.shift(1))

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        return df["sma_fast"] < df["sma_slow"]

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        fast = df["sma_fast"]
        slow = df["sma_slow"]

        return (fast < slow) & (fast.shift(1) >= slow.shift(1))

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        return df["sma_fast"] > df["sma_slow"]


class SmaCrossoverStrategy(BaseComposableStrategy):
    """Minimal SMA crossover strategy for testing."""

    def __init__(self, config: SmaCrossoverConfig | None = None) -> None:
        self._config = config or SmaCrossoverConfig()

        super().__init__(
            indicator_suite=SmaCrossoverSuite(self._config),
            signal_model=SmaCrossoverSignalModel(),
        )

    @property
    def min_bars_required(self) -> int:
        return self._config.slow_period


# ================================
# --> Contract test class
# ================================


class TestSmaCrossoverContracts(
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
):
    """All contract tests for the SMA crossover strategy."""

    manifest = StrategyTestManifest(
        name="SmaCrossover",
        build_strategy=lambda: SmaCrossoverStrategy(SmaCrossoverConfig()),
        config_class=SmaCrossoverConfig,
        min_warmup_bars=30,
    )

