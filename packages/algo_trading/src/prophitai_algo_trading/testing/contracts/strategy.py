"""Strategy integration contract tests.

Validates the full pipeline: strategy instantiation, indicator + signal
flow, entry candidate construction, and score_entries output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import EntryCandidate
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_algo_trading.testing.contracts.constants import SIGNAL_KEYS
from prophitai_algo_trading.testing.fixtures import uptrend

if TYPE_CHECKING:
    from prophitai_algo_trading.testing.manifest import StrategyTestManifest


class StrategyContract:
    """Mixin — inherit and set ``manifest`` to get strategy integration tests."""

    manifest: StrategyTestManifest

    def test_is_composable_strategy(self) -> None:
        """Strategy is an instance of BaseComposableStrategy."""
        strategy = self.manifest.build_strategy()

        assert isinstance(strategy, BaseComposableStrategy)

    def test_min_bars_required_positive(self) -> None:
        """Every real strategy needs warmup — min_bars_required must be > 0."""
        strategy = self.manifest.build_strategy()

        assert strategy.min_bars_required > 0, (
            "min_bars_required should be > 0 for any real strategy"
        )

    def test_full_pipeline(self) -> None:
        """Indicators → signals runs without error and returns 4 bool series."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        enriched = strategy.calculate_indicators(df)
        signals = strategy.generate_signals(enriched)

        assert set(signals.keys()) == SIGNAL_KEYS

        for name, signal in signals.items():
            assert isinstance(signal, pd.Series), f"{name} not a Series"
            assert signal.dtype == bool, f"{name} dtype is {signal.dtype}"

    def test_score_entries_returns_series(self) -> None:
        """score_entries returns a pd.Series with correct length."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        enriched = strategy.calculate_indicators(df)
        scores = strategy.score_entries(enriched)

        assert isinstance(scores, pd.Series)
        assert len(scores) == len(enriched)

    def test_build_entry_candidate(self) -> None:
        """build_entry_candidate produces a valid EntryCandidate."""
        strategy = self.manifest.build_strategy()
        df = uptrend()

        enriched = strategy.calculate_indicators(df)
        row = enriched.iloc[-1]

        candidate = strategy.build_entry_candidate(
            symbol="TEST",
            row=row,
            target_position=1,
            timestamp=enriched.index[-1],
            score=1.0,
        )

        assert isinstance(candidate, EntryCandidate)
        assert candidate.symbol == "TEST"
        assert candidate.target_position == 1
        assert candidate.price > 0
