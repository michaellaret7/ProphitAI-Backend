"""Bollinger Bands and %B indicators wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.volatility import (
    calc_bollinger_bands,
    calc_bollinger_pct_b,
)


class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands — upper, middle (SMA), and lower bands.

    Args:
        df: DataFrame with a close column.
        window: SMA lookback period. Default 20.
        num_std: Number of standard deviations for band width. Default 2.0.
        source_column: Column to compute bands from. Default ``"close"``.
        output_prefix: Prefix for output columns. Default ``"bb"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        num_std: float = 2.0,
        source_column: str = "close",
        output_prefix: str = "bb",
    ):
        self.window = window
        self.num_std = num_std
        self.source_column = source_column
        self.col_upper = f"{output_prefix}_upper"
        self.col_middle = f"{output_prefix}_middle"
        self.col_lower = f"{output_prefix}_lower"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute Bollinger Band columns for the full DataFrame."""
        upper, middle, lower = calc_bollinger_bands(
            self.df[self.source_column],
            window=self.window,
            num_std=self.num_std,
        )
        self.df[self.col_upper] = upper.reindex(self.df.index)
        self.df[self.col_middle] = middle.reindex(self.df.index)
        self.df[self.col_lower] = lower.reindex(self.df.index)
        return self.df


class BollingerPctBIndicator(BaseIndicator):
    """Bollinger %B — normalized position within the bands (0-1).

    Values > 1 = above upper band, < 0 = below lower band.

    Args:
        df: DataFrame with a close column.
        window: SMA lookback period. Default 20.
        num_std: Number of standard deviations. Default 2.0.
        source_column: Column to compute from. Default ``"close"``.
        output_column: Column name for the result. Default ``"bb_pct_b"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        num_std: float = 2.0,
        source_column: str = "close",
        output_column: str = "bb_pct_b",
    ):
        self.window = window
        self.num_std = num_std
        self.source_column = source_column
        self.output_column = output_column
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute Bollinger %B column for the full DataFrame."""
        series = calc_bollinger_pct_b(
            self.df[self.source_column],
            window=self.window,
            num_std=self.num_std,
        )
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df
