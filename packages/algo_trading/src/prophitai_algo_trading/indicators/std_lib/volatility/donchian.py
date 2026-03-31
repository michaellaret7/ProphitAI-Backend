"""Donchian Channels indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.volatility import calc_donchian_channels


class DonchianChannelsIndicator(BaseIndicator):
    """Donchian Channels — breakout detection (Turtle Trading).

    Upper = highest high, Lower = lowest low, Middle = midpoint.

    Args:
        df: DataFrame with high and low columns.
        window: Lookback period. Default 20.
        output_prefix: Prefix for output columns. Default ``"dc"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        output_prefix: str = "dc",
    ):
        self.window = window
        self.col_upper = f"{output_prefix}_upper"
        self.col_middle = f"{output_prefix}_middle"
        self.col_lower = f"{output_prefix}_lower"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute Donchian Channel columns for the full DataFrame."""
        upper, middle, lower = calc_donchian_channels(
            self.df["high"],
            self.df["low"],
            window=self.window,
        )
        self.df[self.col_upper] = upper.reindex(self.df.index)
        self.df[self.col_middle] = middle.reindex(self.df.index)
        self.df[self.col_lower] = lower.reindex(self.df.index)
        return self.df
