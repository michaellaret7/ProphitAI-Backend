"""Z-Score indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.statistical import calc_z_score


class ZScoreIndicator(BaseIndicator):
    """Rolling Z-Score — statistical extreme detection.

    |Z| > 2 = statistically extreme, used for mean-reversion signals.

    Args:
        df: DataFrame with a close column.
        window: Rolling lookback period. Default 50.
        source_column: Column to compute Z-Score from. Default ``"close"``.
        output_column: Column name for the result. Default ``"zscore_{window}"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 50,
        source_column: str = "close",
        output_column: str | None = None,
    ):
        self.window = window
        self.source_column = source_column
        self.output_column = output_column or f"zscore_{window}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute Z-Score column for the full DataFrame."""
        series = calc_z_score(
            self.df[self.source_column],
            window=self.window,
        )
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df
