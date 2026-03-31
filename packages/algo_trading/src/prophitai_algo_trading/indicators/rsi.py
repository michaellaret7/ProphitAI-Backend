"""Relative Strength Index (RSI) indicator using Wilder's smoothing method.

Supports both full batch calculation and efficient incremental updates
for real-time bar-by-bar processing.
"""

import numpy as np
import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator


class RSI(BaseIndicator):
    """RSI indicator with incremental update support.

    Args:
        df: DataFrame with 'close' column.
        period: Lookback period for RSI calculation.
    """

    def __init__(self, df: pd.DataFrame, period: int = 2):
        self.period = period
        super().__init__(df)

    def calculate(self) -> pd.DataFrame:
        """Compute RSI for all rows using Wilder's smoothing method."""
        close = self.df['close']
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        n = len(self.df)

        if n <= self.period:
            self.df['rsi'] = np.nan
            self.df['rsi_avg_gain'] = np.nan
            self.df['rsi_avg_loss'] = np.nan
            return self.df

        rsi_avg_gain = np.full(n, np.nan)
        rsi_avg_loss = np.full(n, np.nan)
        rsi_values = np.full(n, np.nan)

        # Seed: simple average of first `period` gains/losses
        gain_arr = gain.to_numpy()
        loss_arr = loss.to_numpy()

        rsi_avg_gain[self.period] = np.nanmean(gain_arr[1:self.period + 1])
        rsi_avg_loss[self.period] = np.nanmean(loss_arr[1:self.period + 1])

        rsi_values[self.period] = self._compute_rsi(
            rsi_avg_gain[self.period], rsi_avg_loss[self.period]
        )

        # Wilder's recursive smoothing
        for i in range(self.period + 1, n):
            rsi_avg_gain[i] = (rsi_avg_gain[i - 1] * (self.period - 1) + gain_arr[i]) / self.period
            rsi_avg_loss[i] = (rsi_avg_loss[i - 1] * (self.period - 1) + loss_arr[i]) / self.period
            rsi_values[i] = self._compute_rsi(rsi_avg_gain[i], rsi_avg_loss[i])

        self.df['rsi'] = rsi_values
        self.df['rsi_avg_gain'] = rsi_avg_gain
        self.df['rsi_avg_loss'] = rsi_avg_loss

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally compute RSI for only the last row.

        Falls back to full calculation when insufficient data exists.

        Args:
            new_df: Updated DataFrame with the new row appended.

        Returns:
            DataFrame with RSI computed for the last row.
        """
        self.df = new_df
        n = len(self.df)

        # Reason: need at least period+2 rows for incremental (previous avg must exist)
        if n < self.period + 2:
            return self.calculate()

        prev_avg_gain = self.df['rsi_avg_gain'].iloc[-2]
        prev_avg_loss = self.df['rsi_avg_loss'].iloc[-2]

        if pd.isna(prev_avg_gain):
            return self.calculate()

        last_idx = self.df.index[-1]
        change = self.df['close'].iloc[-1] - self.df['close'].iloc[-2]
        current_gain = max(change, 0)
        current_loss = abs(min(change, 0))

        avg_gain = (prev_avg_gain * (self.period - 1) + current_gain) / self.period
        avg_loss = (prev_avg_loss * (self.period - 1) + current_loss) / self.period

        self.df.loc[last_idx, 'rsi_avg_gain'] = avg_gain
        self.df.loc[last_idx, 'rsi_avg_loss'] = avg_loss
        self.df.loc[last_idx, 'rsi'] = self._compute_rsi(avg_gain, avg_loss)

        return self.df

    @staticmethod
    def _compute_rsi(avg_gain: float, avg_loss: float) -> float:
        """Compute RSI value from average gain and loss."""
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        return 100.0
