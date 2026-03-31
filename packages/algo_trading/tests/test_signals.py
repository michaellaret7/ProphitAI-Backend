"""Unit tests for shared signal-model infrastructure."""

from __future__ import annotations

import pandas as pd
import pytest

from prophitai_algo_trading.signals import (
    BaseSignalModel,
    bars_since,
    cooldown_mask,
    cross_above,
    cross_below,
    debounce,
    fired_within,
    stays_above,
)
from prophitai_algo_trading.strategies.rsi_mean_reversion import RSIMeanReversionSignalModel


class _ToySignalModel(BaseSignalModel):
    required_columns = ("close",)

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        enriched = df.copy()
        enriched["above_101"] = enriched["close"] > 101
        return enriched

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        return df["above_101"]

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)


def test_base_signal_model_validates_required_columns() -> None:
    model = _ToySignalModel()

    with pytest.raises(ValueError, match="missing required columns"):
        model.generate(pd.DataFrame({"open": [1.0]}))


def test_base_signal_model_runs_enrich_before_generating_signals() -> None:
    model = _ToySignalModel()
    df = pd.DataFrame({"close": [100.0, 102.0]})

    signals = model.generate(df)

    assert list(signals["long_entry"]) == [False, True]
    assert not signals["short_entry"].any()


def test_rsi_signal_model_generates_expected_signals_and_scores() -> None:
    model = RSIMeanReversionSignalModel(
        rsi_oversold_threshold=10,
        rsi_overbought_threshold=90,
    )
    index = pd.date_range("2025-01-01", periods=3, freq="D")
    df = pd.DataFrame({
        "close": [100.0, 105.0, 95.0],
        "rsi": [5.0, 95.0, 45.0],
        "sma_trend": [99.0, 110.0, 90.0],
        "sma_exit": [101.0, 104.0, 96.0],
    }, index=index)

    signals = model.generate(df)
    scores = model.score_entries(df)

    assert list(signals["long_entry"]) == [True, False, False]
    assert list(signals["short_entry"]) == [False, True, False]
    assert list(signals["long_exit"]) == [False, True, False]
    assert list(signals["short_exit"]) == [True, False, True]
    assert scores.iloc[0] == pytest.approx(45.0)
    assert scores.iloc[1] == pytest.approx(45.0)


def test_cross_primitives_detect_directional_crosses() -> None:
    left = pd.Series([1.0, 2.0, 0.5, 3.0])
    right = pd.Series([1.5, 1.5, 1.0, 2.0])

    assert list(cross_above(left, right)) == [False, True, False, True]
    assert list(cross_below(left, right)) == [False, False, True, False]


def test_bars_since_and_fired_within_track_recent_events() -> None:
    event = pd.Series([False, True, False, False, True, False])

    since = bars_since(event)

    assert pd.isna(since.iloc[0])
    assert list(since.iloc[1:]) == [0.0, 1.0, 2.0, 0.0, 1.0]
    assert list(fired_within(event, lookback=1)) == [False, True, True, False, True, True]
    assert list(fired_within(event, lookback=0)) == [False, True, False, False, True, False]


def test_stays_above_requires_consecutive_confirmation_bars() -> None:
    left = pd.Series([1.0, 2.0, 3.0, 2.5, 1.0])
    right = pd.Series([1.5, 1.5, 1.5, 2.0, 1.5])

    assert list(stays_above(left, right, bars=2)) == [False, False, True, True, False]


def test_cooldown_mask_blocks_reentries_after_trigger() -> None:
    trigger = pd.Series([False, True, False, False, False])

    assert list(cooldown_mask(trigger, bars=2)) == [True, False, False, False, True]


def test_debounce_accepts_first_signal_then_suppresses_repeats() -> None:
    signal = pd.Series([True, True, True, True, False, True])

    assert list(debounce(signal, bars=2)) == [True, False, False, True, False, False]
    assert list(debounce(signal, bars=0)) == [True, True, True, True, False, True]


def test_signal_primitives_validate_bar_arguments() -> None:
    with pytest.raises(ValueError, match="lookback must be >= 0"):
        fired_within(pd.Series([True]), lookback=-1)

    with pytest.raises(ValueError, match="bars must be >= 1"):
        stays_above(pd.Series([1.0]), pd.Series([0.0]), bars=0)
