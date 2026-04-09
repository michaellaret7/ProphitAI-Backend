"""Signal model contract tests.

Validates that a strategy's signal model conforms to the
``BaseSignalModel`` interface: correct keys, bool dtype, proper length,
column validation, and bounded scores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from prophitai_algo_trading.testing.contracts.constants import SIGNAL_KEYS
from prophitai_algo_trading.testing.fixtures import uptrend

if TYPE_CHECKING:
    from prophitai_algo_trading.testing.manifest import StrategyTestManifest


# ================================
# --> Helper funcs
# ================================


def _build_and_enrich(manifest: StrategyTestManifest, fixture_fn):
    """Build a fresh strategy and enrich the fixture with indicators.

    Returns:
        Tuple of (strategy, enriched DataFrame).
    """
    strategy = manifest.build_strategy()
    df = fixture_fn()

    return strategy, strategy.calculate_indicators(df)


class SignalModelContract:
    """Mixin — inherit and set ``manifest`` to get signal model tests."""

    manifest: StrategyTestManifest

    def test_generate_returns_four_keys(self) -> None:
        """generate_signals returns exactly the 4 standard signal keys."""
        strategy, df = _build_and_enrich(self.manifest, uptrend)

        signals = strategy.generate_signals(df)

        assert set(signals.keys()) == SIGNAL_KEYS

    def test_signals_are_bool_series(self) -> None:
        """Each signal is a pd.Series with dtype bool."""
        strategy, df = _build_and_enrich(self.manifest, uptrend)

        signals = strategy.generate_signals(df)

        for name, signal in signals.items():
            assert isinstance(signal, pd.Series), (
                f"{name} is {type(signal).__name__}, not Series"
            )
            assert signal.dtype == bool, (
                f"{name} dtype is {signal.dtype}, not bool"
            )

    def test_signal_length_matches_input(self) -> None:
        """Each signal series has the same length as the input DataFrame."""
        strategy, df = _build_and_enrich(self.manifest, uptrend)

        signals = strategy.generate_signals(df)

        for name, signal in signals.items():
            assert len(signal) == len(df), (
                f"{name} length {len(signal)} != df length {len(df)}"
            )

    def test_missing_columns_raises(self) -> None:
        """Signal model raises ValueError when required columns are missing.

        Tests BaseSignalModel.validate() directly — bypasses the strategy
        wrapper to isolate column validation from indicator calculation.
        """
        strategy = self.manifest.build_strategy()
        model = strategy.signal_model

        if not model.required_columns:
            pytest.skip("No required_columns declared on signal model")

        empty = pd.DataFrame({"close": [100.0]})

        with pytest.raises(ValueError, match="missing required columns"):
            model.generate(empty)

    def test_score_entries_bounded(self) -> None:
        """score_entries returns finite, non-negative values."""
        strategy, df = _build_and_enrich(self.manifest, uptrend)

        scores = strategy.score_entries(df)

        assert isinstance(scores, pd.Series)
        assert scores.notna().all(), "score_entries contains NaN"
        assert (scores >= 0).all(), "score_entries contains negative values"

