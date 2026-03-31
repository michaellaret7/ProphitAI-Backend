"""On-Balance Volume indicator wrapping the calculations package."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.volume import calc_obv


class OBVIndicator(BaseIndicator):
    """On-Balance Volume — cumulative volume signed by price direction.

    Divergence between OBV trend and price trend signals
    accumulation/distribution.

    Args:
        df: DataFrame with close and volume columns.
        output_column: Column name for the result. Default ``"obv"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        output_column: str = "obv",
    ):
        self.output_column = output_column
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute OBV column for the full DataFrame."""
        series = calc_obv(self.df["close"], self.df["volume"])
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update OBV for the last row."""
        self.df = new_df
        if len(self.df) < 2:
            return self.calculate()

        prev_obv = self.df[self.output_column].iloc[-2]
        if pd.isna(prev_obv):
            return self.calculate()

        last_idx = self.df.index[-1]
        delta = self.df["close"].iloc[-1] - self.df["close"].iloc[-2]
        direction = float(np.sign(delta))
        self.df.loc[last_idx, self.output_column] = (
            prev_obv + direction * self.df["volume"].iloc[-1]
        )
        return self.df
