"""Base strategy class for all trading strategies.

Defines the pure strategy interface: strategies receive data and return
signals without owning state, position tracking, or execution context.
"""

from __future__ import annotations

from abc import abstractmethod, ABC

import pandas as pd


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Strategies are pure signal generators. They receive a DataFrame,
    compute indicators, and return entry/exit signals. They do NOT own
    data, track positions, manage warmup, or interact with brokers.

    Subclasses must implement:
        - calculate_indicators(df): Batch indicator calculation.
        - update_indicators(df): Incremental indicator update (last row).
        - generate_signals(df): Return 4 boolean Series dict.
    """

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators on the full DataFrame.

        Args:
            df: OHLCV DataFrame to compute indicators on.

        Returns:
            DataFrame with indicator columns added.
        """

    @abstractmethod
    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicators for the last row only.

        Used by event-driven and live engines after appending a new bar.
        Falls back to calculate_indicators() if no incremental path exists.

        Args:
            df: DataFrame with indicators already computed for prior rows.

        Returns:
            DataFrame with last row's indicators updated.
        """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Generate entry/exit signals for the full DataFrame.

        Args:
            df: DataFrame with indicators already calculated.

        Returns:
            Dict with keys 'long_entry', 'long_exit', 'short_entry',
            'short_exit', each mapping to a boolean pd.Series.
        """

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Score entry signals by conviction strength (higher = stronger).

        Used by engines to rank candidates when more entries fire than
        available position slots. Strategies should override this with
        a metric derived from their indicators (e.g. MACD histogram
        magnitude, RSI extremeness, z-score distance).

        Args:
            df: DataFrame with indicators already calculated.

        Returns:
            Float Series indexed like df. Higher values get fill priority.
        """
        return pd.Series(1.0, index=df.index)

    @property
    def min_bars_required(self) -> int:
        """Minimum bars needed before signals are meaningful.

        Override in subclasses to declare indicator warmup requirements.
        """
        return 0
