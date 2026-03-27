"""MACD (Moving Average Convergence Divergence) indicator.

Supports both full batch calculation and efficient incremental updates
for real-time bar-by-bar processing.

Components:
- Fast EMA (default 12) and Slow EMA (default 26) of close price
- MACD Line = Fast EMA - Slow EMA
- Signal Line = EMA (default 9) of MACD Line
- Histogram = MACD Line - Signal Line
"""

import numpy as np
import pandas as pd

from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class MACD:
    """MACD indicator with incremental update support.

    Args:
        df: DataFrame with 'close' column.
        fast_period: Lookback for fast EMA (default 12).
        slow_period: Lookback for slow EMA (default 26).
        signal_period: Lookback for signal line EMA (default 9).
    """

    def __init__(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        self.df = normalize_columns(df.copy())
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.calculate()

    def calculate(self) -> pd.DataFrame:
        """Compute MACD for all rows using EMA (exponential weighted mean)."""
        close = self.df['close']
        n = len(self.df)

        if n < self.slow_period:
            self.df['ema_fast'] = np.nan
            self.df['ema_slow'] = np.nan
            self.df['macd'] = np.nan
            self.df['macd_signal'] = np.nan
            self.df['macd_histogram'] = np.nan
            return self.df

        self.df['ema_fast'] = close.ewm(span=self.fast_period, adjust=False).mean()
        self.df['ema_slow'] = close.ewm(span=self.slow_period, adjust=False).mean()
        self.df['macd'] = self.df['ema_fast'] - self.df['ema_slow']
        self.df['macd_signal'] = self.df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        self.df['macd_histogram'] = self.df['macd'] - self.df['macd_signal']

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally compute MACD for only the last row.

        Uses the EMA recursive formula: ema = alpha * value + (1 - alpha) * prev_ema

        Falls back to full calculation when insufficient data exists.

        Args:
            new_df: Updated DataFrame with the new row appended.

        Returns:
            DataFrame with MACD computed for the last row.
        """
        self.df = new_df
        n = len(self.df)

        if n < self.slow_period + 2:
            return self.calculate()

        prev_ema_fast = self.df['ema_fast'].iloc[-2]
        prev_ema_slow = self.df['ema_slow'].iloc[-2]
        prev_signal = self.df['macd_signal'].iloc[-2]

        if pd.isna(prev_ema_fast) or pd.isna(prev_ema_slow) or pd.isna(prev_signal):
            return self.calculate()

        last_idx = self.df.index[-1]
        close = self.df['close'].iloc[-1]

        alpha_fast = 2.0 / (self.fast_period + 1)
        alpha_slow = 2.0 / (self.slow_period + 1)
        alpha_signal = 2.0 / (self.signal_period + 1)

        ema_fast = alpha_fast * close + (1 - alpha_fast) * prev_ema_fast
        ema_slow = alpha_slow * close + (1 - alpha_slow) * prev_ema_slow
        macd_val = ema_fast - ema_slow
        signal_val = alpha_signal * macd_val + (1 - alpha_signal) * prev_signal

        self.df.loc[last_idx, 'ema_fast'] = ema_fast
        self.df.loc[last_idx, 'ema_slow'] = ema_slow
        self.df.loc[last_idx, 'macd'] = macd_val
        self.df.loc[last_idx, 'macd_signal'] = signal_val
        self.df.loc[last_idx, 'macd_histogram'] = macd_val - signal_val

        return self.df
