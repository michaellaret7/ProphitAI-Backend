"""Future leakage detection tests — the most critical contract.

A signal at bar N must not change when bars N+1..end are removed.
If any indicator or signal value changes, the strategy has look-ahead
bias and will produce misleading backtest results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from prophitai_algo_trading.testing.contracts.constants import SIGNAL_KEYS
from prophitai_algo_trading.testing.fixtures import (
    OHLCV_COLS,
    downtrend,
    mean_reverting,
    uptrend,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.testing.manifest import StrategyTestManifest


class LeakageContract:
    """Mixin — inherit and set ``manifest`` to get leakage detection tests."""

    manifest: StrategyTestManifest

    @pytest.mark.parametrize("offset", [10, 30, 50])
    @pytest.mark.parametrize(
        "fixture_fn",
        [uptrend, downtrend, mean_reverting],
        ids=["uptrend", "downtrend", "mean_reverting"],
    )
    def test_no_indicator_leakage(self, fixture_fn, offset: int) -> None:
        """Indicator values at bar N are identical on full vs. truncated data.

        Uses fresh strategy instances for each run to avoid
        IndicatorPipeline._instances caching interference.
        """
        test_bar = self.manifest.min_warmup_bars + offset
        df = fixture_fn()

        if test_bar >= len(df):
            pytest.skip(
                f"test_bar {test_bar} exceeds fixture length {len(df)}"
            )

        # Reason: full run — indicators computed on all bars
        strategy_full = self.manifest.build_strategy()
        full_result = strategy_full.calculate_indicators(df.copy())

        # Reason: truncated run — fresh instance, only bars 0..test_bar
        strategy_trunc = self.manifest.build_strategy()
        truncated = df.iloc[: test_bar + 1].copy()
        trunc_result = strategy_trunc.calculate_indicators(truncated)

        indicator_cols = [c for c in full_result.columns if c not in OHLCV_COLS]

        if not indicator_cols:
            pytest.skip("No indicator columns to check")

        full_row = full_result[indicator_cols].iloc[test_bar]
        trunc_row = trunc_result[indicator_cols].iloc[-1]

        pd.testing.assert_series_equal(
            full_row,
            trunc_row,
            atol=1e-10,
            check_names=False,
            obj=f"indicator leakage at bar {test_bar}",
        )

    @pytest.mark.parametrize("offset", [10, 30, 50])
    @pytest.mark.parametrize(
        "fixture_fn",
        [uptrend, downtrend, mean_reverting],
        ids=["uptrend", "downtrend", "mean_reverting"],
    )
    def test_no_signal_leakage(self, fixture_fn, offset: int) -> None:
        """Signals at bar N are identical on full vs. truncated data.

        If a signal changes when future bars are removed, the strategy
        is using future information — this is the cardinal sin of
        quantitative finance.
        """
        test_bar = self.manifest.min_warmup_bars + offset
        df = fixture_fn()

        if test_bar >= len(df):
            pytest.skip(
                f"test_bar {test_bar} exceeds fixture length {len(df)}"
            )

        # Reason: full run
        strategy_full = self.manifest.build_strategy()
        full_enriched = strategy_full.calculate_indicators(df.copy())
        full_signals = strategy_full.generate_signals(full_enriched)

        # Reason: truncated run with fresh strategy
        strategy_trunc = self.manifest.build_strategy()
        truncated = df.iloc[: test_bar + 1].copy()
        trunc_enriched = strategy_trunc.calculate_indicators(truncated)
        trunc_signals = strategy_trunc.generate_signals(trunc_enriched)

        for key in SIGNAL_KEYS:
            full_val = full_signals[key].iloc[test_bar]
            trunc_val = trunc_signals[key].iloc[-1]

            assert full_val == trunc_val, (
                f"Future leakage in '{key}' at bar {test_bar}: "
                f"full={full_val}, truncated={trunc_val}"
            )
