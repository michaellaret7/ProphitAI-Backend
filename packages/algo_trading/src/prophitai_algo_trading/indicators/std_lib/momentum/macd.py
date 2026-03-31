"""MACD indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.momentum import calc_macd


class MACDIndicator(BaseIndicator):
    """MACD line, signal line, and histogram.

    Args:
        df: DataFrame with a close column.
        fast: Fast EMA span. Default 12.
        slow: Slow EMA span. Default 26.
        signal_span: Signal line EMA span. Default 9.
        source_column: Column to compute MACD from. Default ``"close"``.
        output_prefix: Prefix for output columns. Default ``"macd"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal_span: int = 9,
        source_column: str = "close",
        output_prefix: str = "macd",
    ):
        self.fast = fast
        self.slow = slow
        self.signal_span = signal_span
        self.source_column = source_column
        self.col_line = f"{output_prefix}_line"
        self.col_signal = f"{output_prefix}_signal"
        self.col_histogram = f"{output_prefix}_histogram"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute MACD columns for the full DataFrame."""
        line, signal, histogram = calc_macd(
            self.df[self.source_column],
            fast=self.fast,
            slow=self.slow,
            signal_span=self.signal_span,
        )
        self.df[self.col_line] = line.reindex(self.df.index)
        self.df[self.col_signal] = signal.reindex(self.df.index)
        self.df[self.col_histogram] = histogram.reindex(self.df.index)
        return self.df
