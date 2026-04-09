"""Indicator suite contract tests.

Validates that a strategy's indicator suite conforms to the
``BaseIndicatorSuite`` interface: columns are added, NaN-free after
warmup, OHLCV is preserved, and the incremental path matches batch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from prophitai_algo_trading.testing.fixtures import (
    OHLCV_COLS,
    downtrend,
    flat,
    mean_reverting,
    uptrend,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.testing.manifest import StrategyTestManifest


# ================================
# --> Helper funcs
# ================================


def _indicator_cols(result: pd.DataFrame) -> list[str]:
    """Return column names added by indicators (non-OHLCV)."""
    return [c for c in result.columns if c not in OHLCV_COLS]


class IndicatorSuiteContract:
    """Mixin — inherit and set ``manifest`` to get indicator suite tests."""

    manifest: StrategyTestManifest

    def test_calculate_returns_dataframe(self) -> None:
        """calculate_indicators returns a pd.DataFrame."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        result = strategy.calculate_indicators(df)

        assert isinstance(result, pd.DataFrame)

    def test_calculate_adds_columns(self) -> None:
        """Indicator suite adds at least one column beyond OHLCV."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        result = strategy.calculate_indicators(df)
        new_cols = _indicator_cols(result)

        assert len(new_cols) > 0, "Indicator suite added no columns"

    def test_no_nan_after_warmup(self) -> None:
        """No NaN values in indicator columns after warmup period."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        result = strategy.calculate_indicators(df)
        after_warmup = result.iloc[self.manifest.min_warmup_bars:]
        indicator_cols = _indicator_cols(result)

        nan_counts = after_warmup[indicator_cols].isna().sum()
        bad = nan_counts[nan_counts > 0]

        assert bad.empty, f"NaN after warmup in: {bad.to_dict()}"

    def test_preserves_ohlcv(self) -> None:
        """OHLCV columns are unchanged after indicator calculation."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        result = strategy.calculate_indicators(df.copy())

        for col in OHLCV_COLS:
            pd.testing.assert_series_equal(
                result[col], df[col], check_names=False,
            )

    def test_update_last_row_matches_calculate(self) -> None:
        """Incremental path produces identical last-row values as batch.

        Critical for live/backtest parity — ensures the fast
        ``update_last_row`` path does not diverge from full recalculation.
        """
        strategy = self.manifest.build_strategy()
        df = uptrend()

        full_result = strategy.calculate_indicators(df.copy())
        update_result = strategy.indicator_suite.update_last_row(df.copy())

        indicator_cols = _indicator_cols(full_result)

        pd.testing.assert_series_equal(
            full_result[indicator_cols].iloc[-1],
            update_result[indicator_cols].iloc[-1],
            atol=1e-10,
            check_names=False,
        )

    def test_idempotent(self) -> None:
        """Calling calculate_indicators twice yields identical results."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        first = strategy.calculate_indicators(df.copy())
        second = strategy.calculate_indicators(df.copy())

        pd.testing.assert_frame_equal(first, second)

    @pytest.mark.parametrize(
        "fixture_fn",
        [uptrend, downtrend, mean_reverting, flat],
        ids=["uptrend", "downtrend", "mean_reverting", "flat"],
    )
    def test_runs_on_all_fixtures(self, fixture_fn) -> None:
        """Indicator suite runs without error on varied market shapes."""
        strategy = self.manifest.build_strategy()
        df = fixture_fn()

        result = strategy.calculate_indicators(df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)
