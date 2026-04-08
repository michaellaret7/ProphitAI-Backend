"""Rolling maximum indicator for 52-week-high and similar signals."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator


class RollingMaxIndicator(BaseIndicator):
    """Rolling maximum of a source column over a lookback window.

    Computes the rolling maximum and a ratio (current / rolling_max) useful
    for proximity-to-high signals (e.g., 52-week-high ratio >= 0.90).

    Args:
        df: DataFrame with the source column.
        window: Lookback period in bars. Default 252 (approx 1 year).
        source_column: Column to compute rolling max over. Default ``"close"``.
        output_column: Name for the rolling-max column. Default ``"rolling_max_{window}"``.
        ratio_column: Name for the ratio column (current / max).
            Default ``"rolling_max_ratio_{window}"``. Set to ``None`` to skip.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 252,
        source_column: str = "close",
        output_column: str | None = None,
        ratio_column: str | None = "auto",
    ):
        self.window = window
        self.source_column = source_column
        self.output_column = output_column or f"rolling_max_{window}"
        self.ratio_column = (
            f"rolling_max_ratio_{window}" if ratio_column == "auto" else ratio_column
        )

        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute rolling max and optional ratio columns."""
        source = self.df[self.source_column]

        rolling_max = source.rolling(window=self.window, min_periods=1).max()

        self.df[self.output_column] = rolling_max.reindex(self.df.index)

        if self.ratio_column is not None:
            self.df[self.ratio_column] = (source / rolling_max).reindex(self.df.index)

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Optimised single-row update."""
        self.df = new_df

        if len(self.df) < 1:
            return self.calculate()

        last_idx = self.df.index[-1]
        window_slice = self.df[self.source_column].iloc[-self.window:]

        rolling_max = window_slice.max()
        self.df.loc[last_idx, self.output_column] = rolling_max

        if self.ratio_column is not None:
            current = self.df.loc[last_idx, self.source_column]
            self.df.loc[last_idx, self.ratio_column] = (
                current / rolling_max if rolling_max != 0 else 0.0
            )

        return self.df
