"""Reusable moving-average indicators backed by the shared calculations package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_calculations.technicals.trend import calc_ema, calc_sma


class SimpleMovingAverageIndicator(BaseIndicator):
    """Rolling SMA indicator with configurable input/output columns."""

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        source_column: str = "close",
        output_column: str | None = None,
    ):
        self.window = window
        self.source_column = source_column
        self.output_column = output_column or f"sma_{window}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        series = calc_sma(self.df[self.source_column], window=self.window)
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        self.df = new_df
        if len(self.df) < self.window:
            return self.calculate()

        last_idx = self.df.index[-1]
        self.df.loc[last_idx, self.output_column] = (
            self.df[self.source_column].iloc[-self.window:].mean()
        )
        return self.df


class ExponentialMovingAverageIndicator(BaseIndicator):
    """EMA indicator with configurable input/output columns."""

    def __init__(
        self,
        df: pd.DataFrame,
        span: int = 20,
        source_column: str = "close",
        output_column: str | None = None,
    ):
        self.span = span
        self.source_column = source_column
        self.output_column = output_column or f"ema_{span}"
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        series = calc_ema(self.df[self.source_column], span=self.span)
        self.df[self.output_column] = series.reindex(self.df.index)
        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        self.df = new_df
        if len(self.df) < 2:
            return self.calculate()

        prev_value = self.df[self.output_column].iloc[-2]
        if pd.isna(prev_value):
            return self.calculate()

        alpha = 2.0 / (self.span + 1)
        price = self.df[self.source_column].iloc[-1]
        last_idx = self.df.index[-1]
        self.df.loc[last_idx, self.output_column] = alpha * price + (1 - alpha) * prev_value
        return self.df
