"""Volume-Weighted Average Price indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.volume import calc_vwap


class VWAPIndicator(BaseIndicator):
    """Rolling VWAP — institutional execution benchmark.

    Price above VWAP = bullish bias, below = bearish bias.

    Args:
        df: DataFrame with high, low, close, volume columns.
        window: Rolling window for VWAP. Default 20.
        output_column: Column name for the result. Default ``"vwap_{window}"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        output_column: str | None = None,
    ):
        self.window = window
        self.output_column = output_column or f"vwap_{window}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute VWAP column for the full DataFrame."""
        series = calc_vwap(
            self.df["high"],
            self.df["low"],
            self.df["close"],
            self.df["volume"],
            window=self.window,
        )
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df
