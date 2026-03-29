import pandas as pd
import numpy as np

from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class IchimokuCloud:
    """
    Ichimoku Cloud indicator calculations and signal generation.

    Parameters:
        df: DataFrame with 'high', 'low', 'close' columns
        tenkan_period: Conversion line period (default 9)
        kijun_period: Base line period (default 26)
        senkou_b_period: Senkou Span B period (default 52)
    """

    def __init__(
        self,
        df: pd.DataFrame,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
    ):
        self.df = normalize_columns(df.copy())
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period

        # Compute Ichimoku indicators on initialization
        self.calculate()

    def calculate(self) -> None:
        """Compute all Ichimoku indicators and store in the dataframe."""
        high = self.df['high']
        low = self.df['low']

        # Tenkan-sen (Conversion Line)
        self.df['tenkan'] = (
            high.rolling(self.tenkan_period).max() +
            low.rolling(self.tenkan_period).min()
        ) / 2

        # Kijun-sen (Base Line)
        self.df['kijun'] = (
            high.rolling(self.kijun_period).max() +
            low.rolling(self.kijun_period).min()
        ) / 2

        # Senkou Span A (Leading Span A) - shifted forward by kijun_period
        self.df['senkou_a'] = (
            (self.df['tenkan'] + self.df['kijun']) / 2
        ).shift(self.kijun_period)

        # Senkou Span B (Leading Span B) - shifted forward by kijun_period
        self.df['senkou_b'] = (
            (high.rolling(self.senkou_b_period).max() +
             low.rolling(self.senkou_b_period).min()) / 2
        ).shift(self.kijun_period)

        # Cloud boundaries
        self.df['cloud_top'] = self.df[['senkou_a', 'senkou_b']].max(axis=1)
        self.df['cloud_bottom'] = self.df[['senkou_a', 'senkou_b']].min(axis=1)

        # Cloud color (trend indication)
        self.df['cloud_color'] = np.where(
            self.df['senkou_a'] >= self.df['senkou_b'], 'green', 'red'
        )

        self.df['price_position'] = np.where(
            self.df['close'] > self.df['cloud_top'], 'above',
            np.where(self.df['close'] < self.df['cloud_bottom'], 'below', 'inside')
        )

        # Price above cloud condition
        self.df['above_cloud'] = self.df['close'] > self.df['cloud_top']

        # Tenkan crosses above Kijun (bullish crossover)
        self.df['tenkan_cross'] = (
            (self.df['tenkan'] > self.df['kijun']) &
            (self.df['tenkan'].shift(1) <= self.df['kijun'].shift(1))
        )

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators for only the last row using existing data for lookbacks.
        Much more efficient than recalculating the entire dataframe.

        Args:
            new_df: The updated dataframe with the new row appended

        Returns:
            The dataframe with indicators calculated for the last row
        """
        self.df = new_df
        n = len(self.df)
        min_required = self.senkou_b_period + self.kijun_period

        if n < min_required:
            return self.calculate()

        last_idx = self.df.index[-1]

        # Tenkan for last row (need last tenkan_period rows)
        tenkan = (
            self.df['high'].iloc[-self.tenkan_period:].max() +
            self.df['low'].iloc[-self.tenkan_period:].min()
        ) / 2

        # Kijun for last row (need last kijun_period rows)
        kijun = (
            self.df['high'].iloc[-self.kijun_period:].max() +
            self.df['low'].iloc[-self.kijun_period:].min()
        ) / 2

        # Senkou A at current row = (tenkan + kijun)/2 from kijun_period ago
        senkou_a = (
            self.df['tenkan'].iloc[-self.kijun_period - 1] +
            self.df['kijun'].iloc[-self.kijun_period - 1]
        ) / 2

        # Senkou B at current row = 52-period calc from kijun_period ago
        start_idx = -self.kijun_period - self.senkou_b_period
        end_idx = -self.kijun_period
        senkou_b = (
            self.df['high'].iloc[start_idx:end_idx].max() +
            self.df['low'].iloc[start_idx:end_idx].min()
        ) / 2

        # Update indicator columns for the last row
        self.df.loc[last_idx, 'tenkan'] = tenkan
        self.df.loc[last_idx, 'kijun'] = kijun
        self.df.loc[last_idx, 'senkou_a'] = senkou_a
        self.df.loc[last_idx, 'senkou_b'] = senkou_b

        # Cloud calculations
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        self.df.loc[last_idx, 'cloud_top'] = cloud_top
        self.df.loc[last_idx, 'cloud_bottom'] = cloud_bottom
        self.df.loc[last_idx, 'cloud_color'] = 'green' if senkou_a >= senkou_b else 'red'

        # Price position relative to cloud
        close = self.df['close'].iloc[-1]
        if close > cloud_top:
            self.df.loc[last_idx, 'price_position'] = 'above'
        elif close < cloud_bottom:
            self.df.loc[last_idx, 'price_position'] = 'below'
        else:
            self.df.loc[last_idx, 'price_position'] = 'inside'

        self.df.loc[last_idx, 'above_cloud'] = close > cloud_top

        # Tenkan cross (need previous row values)
        if n >= 2:
            prev_tenkan = self.df['tenkan'].iloc[-2]
            prev_kijun = self.df['kijun'].iloc[-2]
            self.df.loc[last_idx, 'tenkan_cross'] = (tenkan > kijun) and (prev_tenkan <= prev_kijun)
        else:
            self.df.loc[last_idx, 'tenkan_cross'] = False

        return self.df


