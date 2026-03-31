"""Unit tests for indicator composition and strategy-local suites."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.indicators import IndicatorPipeline, IndicatorSpec


class _DummyStrategy(BaseStrategy):
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        empty = pd.Series(False, index=df.index)
        return {
            "long_entry": empty,
            "long_exit": empty,
            "short_entry": empty,
            "short_exit": empty,
        }


def _sample_ohlcv(periods: int = 12) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=periods, freq="D")
    close = pd.Series(
        [100.0, 101.0, 103.0, 102.0, 104.0, 107.0, 106.0, 108.0, 111.0, 109.0, 112.0, 114.0][:periods],
        index=index,
    )
    return pd.DataFrame({
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": [1_000.0 + i * 10 for i in range(periods)],
    }, index=index)


def test_indicator_pipeline_composes_shared_indicators() -> None:
    pipeline = IndicatorPipeline([
        IndicatorSpec("rsi", {"period": 2}),
        IndicatorSpec("sma", {"window": 3, "output_column": "sma_fast"}),
    ])

    enriched = pipeline.calculate(_sample_ohlcv(8))

    assert "rsi" in enriched.columns
    assert "sma_fast" in enriched.columns
    assert enriched["sma_fast"].iloc[-1] == pytest.approx((107.0 + 106.0 + 108.0) / 3)


def test_indicator_pipeline_incremental_update_matches_full_recalculation() -> None:
    initial = _sample_ohlcv(8)
    appended = _sample_ohlcv(9)

    pipeline = IndicatorPipeline([
        IndicatorSpec("rsi", {"period": 2}),
        IndicatorSpec("sma", {"window": 3, "output_column": "sma_fast"}),
    ])

    pipeline.calculate(initial)
    updated = pipeline.update_last_row(appended.copy())

    fresh = IndicatorPipeline([
        IndicatorSpec("rsi", {"period": 2}),
        IndicatorSpec("sma", {"window": 3, "output_column": "sma_fast"}),
    ]).calculate(appended.copy())

    assert updated["rsi"].iloc[-1] == pytest.approx(fresh["rsi"].iloc[-1])
    assert updated["sma_fast"].iloc[-1] == pytest.approx(fresh["sma_fast"].iloc[-1])


def test_base_strategy_build_entry_candidate_uses_chandelier_stop_columns() -> None:
    strategy = _DummyStrategy()
    row = pd.Series({
        "close": 101.0,
        "volume": 2_000.0,
        "chandelier_long_stop": 96.5,
        "or_low": 95.0,
    })

    candidate = strategy.build_entry_candidate(
        symbol="AAPL",
        row=row,
        target_position=1,
        timestamp=datetime(2025, 1, 1),
        score=2.0,
    )

    assert candidate.direction == Direction.LONG
    assert candidate.stop_price == pytest.approx(96.5)
    assert candidate.stop_distance == pytest.approx(4.5)
