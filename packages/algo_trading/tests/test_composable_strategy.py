"""Tests for the composable strategy base."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from prophitai_algo_trading.indicators import BaseIndicatorSuite, IndicatorSpec
from prophitai_algo_trading.signals import BaseSignalModel
from prophitai_algo_trading.strategies import BaseComposableStrategy


class _ToyIndicatorSuite(BaseIndicatorSuite):
    def __init__(self) -> None:
        self.calculate_calls = 0
        self.update_calls = 0
        super().__init__()

    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        return ()

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        self.calculate_calls += 1
        enriched = df.copy()
        enriched["toy_feature"] = pd.Series(range(len(enriched)), index=enriched.index, dtype=float)
        return enriched

    def update_last_row(self, df: pd.DataFrame) -> pd.DataFrame:
        self.update_calls += 1
        enriched = df.copy()
        if "toy_feature" not in enriched.columns:
            enriched["toy_feature"] = 0.0
        enriched.iloc[-1, enriched.columns.get_loc("toy_feature")] = 1.0
        return enriched


class _ToySignalModel(BaseSignalModel):
    required_columns = ("toy_feature",)

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        return df["toy_feature"] > 0.5

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        return df["toy_feature"] < 0.5

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        self.validate(df)
        return df["toy_feature"] * 10.0


class _ToyComposableStrategy(BaseComposableStrategy):
    def __init__(self) -> None:
        self._toy_indicator_suite = _ToyIndicatorSuite()
        self._toy_signal_model = _ToySignalModel()
        super().__init__(
            indicator_suite=self._toy_indicator_suite,
            signal_model=self._toy_signal_model,
        )

    @property
    def min_bars_required(self) -> int:
        return 5


def test_composable_strategy_delegates_indicator_and_signal_work() -> None:
    strategy = _ToyComposableStrategy()
    index = pd.date_range("2025-01-01", periods=2, freq="D")
    df = pd.DataFrame({"close": [100.0, 101.0]}, index=index)

    enriched = strategy.calculate_indicators(df)
    signals = strategy.generate_signals(enriched)
    scores = strategy.score_entries(enriched)

    assert strategy.indicator_suite is strategy._toy_indicator_suite
    assert strategy.signal_model is strategy._toy_signal_model
    assert strategy._toy_indicator_suite.calculate_calls == 1
    assert list(signals["long_entry"]) == [False, True]
    assert list(signals["long_exit"]) == [True, False]
    assert list(scores) == [0.0, 10.0]
    assert strategy.min_bars_required == 5


def test_composable_strategy_update_delegates_to_indicator_suite() -> None:
    strategy = _ToyComposableStrategy()
    initial_index = pd.date_range("2025-01-01", periods=2, freq="D")
    initial = pd.DataFrame({"close": [100.0, 101.0]}, index=initial_index)
    appended_index = pd.date_range("2025-01-01", periods=3, freq="D")
    appended = pd.DataFrame({"close": [100.0, 101.0, 102.0]}, index=appended_index)

    strategy.calculate_indicators(initial)
    updated = strategy.update_indicators(appended)

    assert strategy._toy_indicator_suite.update_calls == 1
    assert updated["toy_feature"].iloc[-1] == 1.0
