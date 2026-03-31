"""Average True Range indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.volatility import calc_atr


class ATRIndicator(BaseIndicator):
    """Average True Range — volatility in price units.

    Args:
        df: DataFrame with high, low, close columns.
        window: ATR lookback period. Default 14.
        output_column: Column name for the result. Default ``"atr_{window}"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 14,
        output_column: str | None = None,
    ):
        self.window = window
        self.output_column = output_column or f"atr_{window}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute ATR column for the full DataFrame."""
        series = calc_atr(
            self.df["high"],
            self.df["low"],
            self.df["close"],
            window=self.window,
        )
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df
