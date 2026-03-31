"""Rate of Change indicator wrapping the calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.momentum import calc_roc


class RateOfChangeIndicator(BaseIndicator):
    """Rate of Change — percentage price change over a lookback window.

    Defaults to ``window=20, skip_recent=0`` for bar-level trading signals.
    The calculations package defaults to 252/21 (academic momentum factor);
    this indicator overrides those defaults for shorter-term use.

    Args:
        df: DataFrame with a close column.
        window: Lookback period in bars. Default 20.
        skip_recent: Bars to skip at the end. Default 0.
        source_column: Column to compute ROC from. Default ``"close"``.
        output_column: Column name for the result. Default ``"roc_{window}"``.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        skip_recent: int = 0,
        source_column: str = "close",
        output_column: str | None = None,
    ):
        self.window = window
        self.skip_recent = skip_recent
        self.source_column = source_column
        self.output_column = output_column or f"roc_{window}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute ROC column for the full DataFrame."""
        series = calc_roc(
            self.df[self.source_column],
            window=self.window,
            skip_recent=self.skip_recent,
        )
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df
