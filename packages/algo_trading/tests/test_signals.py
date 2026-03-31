"""Unit tests for shared signal-model infrastructure."""

from __future__ import annotations

import pandas as pd
import pytest

from prophitai_algo_trading.signals import BaseSignalModel
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
