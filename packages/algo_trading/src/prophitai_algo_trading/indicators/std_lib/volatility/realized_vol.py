"""Realized (historical) volatility indicator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator


class RealizedVolIndicator(BaseIndicator):
    """Annualized realized volatility from log returns.

    Computes: close.pct_change().rolling(window).std() * sqrt(annualization_factor)

    The default output column is ``"realized_vol"`` which is auto-detected by
    ``VolatilityTargetSizer`` for position sizing.

    Args:
        df: DataFrame with the source column.
        window: Lookback period for rolling std. Default 20.
        source_column: Column to compute returns from. Default ``"close"``.
        output_column: Name for the volatility column.
            Default ``"realized_vol"``.
        annualization_factor: Trading days per year. Default 252.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        source_column: str = "close",
        output_column: str = "realized_vol",
        annualization_factor: int = 252,
    ):
        self.window = window
        self.source_column = source_column
        self.output_column = output_column
        self.annualization_factor = annualization_factor

        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute annualized realized volatility for the full DataFrame."""
        returns = self.df[self.source_column].pct_change()

        rolling_std = returns.rolling(window=self.window, min_periods=self.window).std()

        self.df[self.output_column] = (
            rolling_std * np.sqrt(self.annualization_factor)
        ).reindex(self.df.index)

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Optimised single-row update."""
        self.df = new_df

        if len(self.df) < self.window + 1:
            return self.calculate()

        last_idx = self.df.index[-1]
        returns = self.df[self.source_column].iloc[-(self.window + 1):].pct_change().dropna()

        self.df.loc[last_idx, self.output_column] = (
            returns.std() * np.sqrt(self.annualization_factor)
        )

        return self.df
