"""Example custom indicator for the strategy scaffold.

Demonstrates how to subclass ``BaseIndicator`` when the shared registry
(sma, ema, rsi) doesn't cover your needs.  Pass the class directly to
``IndicatorSpec`` instead of a string key::

    IndicatorSpec(
        indicator=BollingerBandIndicator,
        params={"window": 20, "num_std": 2.0},
    )
"""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.indicators import BaseIndicator


class BollingerBandIndicator(BaseIndicator):
    """Bollinger Bands — SMA ± N standard deviations.

    Output columns:
        bb_middle  — rolling SMA of *source_column*
        bb_upper   — middle + num_std * rolling std
        bb_lower   — middle - num_std * rolling std
        bb_width   — (upper - lower) / middle  (normalized bandwidth)
    """

    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 20,
        num_std: float = 2.0,
        source_column: str = "close",
    ) -> None:
        self.window = window
        self.num_std = num_std
        self.source_column = source_column
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute Bollinger Bands for the full DataFrame."""
        source = self.df[self.source_column]
        rolling = source.rolling(window=self.window)

        middle = rolling.mean()
        std = rolling.std(ddof=0)

        self.df["bb_middle"] = middle
        self.df["bb_upper"] = middle + self.num_std * std
        self.df["bb_lower"] = middle - self.num_std * std
        self.df["bb_width"] = ((self.df["bb_upper"] - self.df["bb_lower"]) / middle).fillna(0.0)

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update only the last row's Bollinger values."""
        self.df = new_df

        if len(self.df) < self.window:
            return self.calculate()

        last_idx = self.df.index[-1]
        tail = self.df[self.source_column].iloc[-self.window :]

        middle = tail.mean()
        std = tail.std(ddof=0)
        upper = middle + self.num_std * std
        lower = middle - self.num_std * std

        self.df.loc[last_idx, "bb_middle"] = middle
        self.df.loc[last_idx, "bb_upper"] = upper
        self.df.loc[last_idx, "bb_lower"] = lower
        self.df.loc[last_idx, "bb_width"] = (upper - lower) / middle if middle else 0.0

        return self.df
