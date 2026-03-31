"""Average Directional Index indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.momentum import calc_adx


class ADXIndicator(BaseIndicator):
    """Average Directional Index — trend strength (0-100).

    ADX < 20 = no trend, > 25 = trending, > 40 = strong trend.

    Args:
        df: DataFrame with high, low, close columns.
        window: ADX lookback period. Default 14.
        output_column: Column name for the result. Default ``"adx_{window}"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 14,
        output_column: str | None = None,
    ):
        self.window = window
        self.output_column = output_column or f"adx_{window}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute ADX column for the full DataFrame."""
        series = calc_adx(
            self.df["high"],
            self.df["low"],
            self.df["close"],
            window=self.window,
        )
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df
