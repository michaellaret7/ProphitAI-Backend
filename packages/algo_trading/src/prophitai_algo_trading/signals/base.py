"""Base contract for sophisticated signal models."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


SignalDict = dict[str, pd.Series]


class BaseSignalModel(ABC):
    """Abstract base for strategy signal models.

    Signal models convert enriched market data into the standard four output
    streams consumed by trading strategies:
    ``long_entry``, ``long_exit``, ``short_entry``, ``short_exit``.

    Keep simple leaf predicates as plain functions. Use this class for
    richer, algorithmic signal logic that benefits from:
    - required-column validation
    - optional signal-state enrichment
    - a standard ``generate`` interface
    - shared entry scoring
    """

    required_columns: tuple[str, ...] = ()

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optionally add signal-state columns before signal generation."""
        return df

    def validate(self, df: pd.DataFrame) -> None:
        """Ensure all required columns are present before generating signals."""
        missing = [column for column in self.required_columns if column not in df.columns]
        if missing:
            raise ValueError(
                f"{self.__class__.__name__} missing required columns: {missing}"
            )

    def generate(self, df: pd.DataFrame) -> SignalDict:
        """Run validation and return the standard 4-way signal dictionary."""
        self.validate(df)
        enriched = self.enrich(df)
        return {
            "long_entry": self._coerce_signal(self.long_entry(enriched), enriched.index),
            "long_exit": self._coerce_signal(self.long_exit(enriched), enriched.index),
            "short_entry": self._coerce_signal(self.short_entry(enriched), enriched.index),
            "short_exit": self._coerce_signal(self.short_exit(enriched), enriched.index),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Score entry signals by conviction. Override in subclasses."""
        self.validate(df)
        enriched = self.enrich(df)
        return pd.Series(1.0, index=enriched.index, dtype=float)

    @abstractmethod
    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        """Return long-entry signal series."""

    @abstractmethod
    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        """Return long-exit signal series."""

    @abstractmethod
    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        """Return short-entry signal series."""

    @abstractmethod
    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        """Return short-exit signal series."""

    @staticmethod
    def _coerce_signal(signal: pd.Series, index: pd.Index) -> pd.Series:
        """Normalize signal outputs to boolean Series aligned to the frame."""
        if not isinstance(signal, pd.Series):
            raise TypeError("Signal outputs must be pandas Series")
        aligned = signal.reindex(index).fillna(False)
        return aligned.astype(bool)
