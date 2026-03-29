"""TTM Squeeze Breakout indicator suite.

Combines Bollinger Bands, Keltner Channels, Donchian Channels, ATR,
RSI, and Chandelier Exit for high-Sharpe breakout detection.

Components:
- Bollinger Bands: SMA(20) +/- 2.0 * StdDev for volatility squeeze detection
- BB Width Percentile: ranks current BB width vs 252-bar history
- Keltner Channels: EMA(20) +/- 1.5 * ATR(20) as the squeeze boundary
- Donchian Channel: Highest-high / lowest-low over N bars for breakout levels
- ATR(14): Average True Range for stop-loss placement and volatility filtering
- Momentum: Linear regression of midpoint deviation for directional bias
- RSI(14): Overbought/oversold for mean reversion exits
- Chandelier Exit: Highest-high(22) - 2.5*ATR(14) for trailing stop
- Squeeze Duration: consecutive bars of squeeze for quality filtering
"""

import numpy as np
import pandas as pd

from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class SqueezeBreakoutIndicator:
    """TTM Squeeze Breakout indicator with incremental update support.

    Args:
        df: DataFrame with OHLCV columns.
        bb_period: Bollinger Band SMA period.
        bb_std: Bollinger Band standard deviation multiplier.
        kc_period: Keltner Channel EMA period.
        kc_atr_mult: Keltner Channel ATR multiplier.
        donchian_period: Donchian Channel lookback.
        atr_period: ATR period for stops and volatility.
        momentum_period: Linear regression period for squeeze momentum.
        volume_ma_period: Volume moving average period for confirmation.
        rsi_period: RSI period for overbought detection.
        chandelier_period: Highest-high lookback for Chandelier exit.
        chandelier_mult: ATR multiplier for Chandelier exit.
        bbw_percentile_lookback: Lookback for BB Width percentile ranking.
        trend_sma_period: SMA period for trend filter (50 for daily, 200 for 15min).
    """

    def __init__(
        self,
        df: pd.DataFrame,
        bb_period: int = 20,
        bb_std: float = 2.0,
        kc_period: int = 20,
        kc_atr_mult: float = 1.5,
        donchian_period: int = 20,
        atr_period: int = 14,
        momentum_period: int = 20,
        volume_ma_period: int = 20,
        rsi_period: int = 14,
        chandelier_period: int = 22,
        chandelier_mult: float = 3.0,
        bbw_percentile_lookback: int = 252,
        trend_sma_period: int = 50,
    ):
        self.df = normalize_columns(df.copy())
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.kc_period = kc_period
        self.kc_atr_mult = kc_atr_mult
        self.donchian_period = donchian_period
        self.atr_period = atr_period
        self.momentum_period = momentum_period
        self.volume_ma_period = volume_ma_period
        self.rsi_period = rsi_period
        self.chandelier_period = chandelier_period
        self.chandelier_mult = chandelier_mult
        self.bbw_percentile_lookback = bbw_percentile_lookback
        self.trend_sma_period = trend_sma_period
        self.calculate()

    def calculate(self) -> pd.DataFrame:
        """Compute all squeeze breakout indicators for all rows."""
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        volume = self.df['volume']
        n = len(self.df)

        min_required = max(self.bb_period, self.kc_period, self.donchian_period, self.atr_period)
        if n < min_required:
            for col in self._indicator_columns():
                self.df[col] = np.nan
            return self.df

        # Reason: ATR uses true range (max of 3 range measures)
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        self.df['atr'] = tr.rolling(self.atr_period).mean()

        # Bollinger Bands
        self.df['bb_mid'] = close.rolling(self.bb_period).mean()
        bb_std_val = close.rolling(self.bb_period).std()
        self.df['bb_upper'] = self.df['bb_mid'] + self.bb_std * bb_std_val
        self.df['bb_lower'] = self.df['bb_mid'] - self.bb_std * bb_std_val

        # Reason: BB Width and its percentile rank — filters for high-quality squeezes
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / self.df['bb_mid']
        self.df['bbw_percentile'] = self.df['bb_width'].rolling(
            window=min(self.bbw_percentile_lookback, n),
            min_periods=20,
        ).rank(pct=True) * 100

        # Keltner Channels (EMA-based)
        self.df['kc_mid'] = close.ewm(span=self.kc_period, adjust=False).mean()
        self.df['kc_upper'] = self.df['kc_mid'] + self.kc_atr_mult * self.df['atr']
        self.df['kc_lower'] = self.df['kc_mid'] - self.kc_atr_mult * self.df['atr']

        # Reason: squeeze is ON when BBs are inside KCs (volatility compressed)
        self.df['squeeze_on'] = (
            (self.df['bb_upper'] < self.df['kc_upper']) &
            (self.df['bb_lower'] > self.df['kc_lower'])
        )

        # Reason: count consecutive squeeze bars for minimum duration filter
        squeeze_arr = self.df['squeeze_on'].astype(int).values
        duration = np.zeros(n, dtype=int)
        for i in range(1, n):
            if squeeze_arr[i]:
                duration[i] = duration[i - 1] + 1
            else:
                duration[i] = 0
        self.df['squeeze_duration'] = duration

        # Reason: squeeze fires when it transitions from ON to OFF
        self.df['squeeze_fired'] = (
            (~self.df['squeeze_on']) & (self.df['squeeze_on'].shift(1) == True)  # noqa: E712
        )

        # Reason: quality squeeze fired — only count squeezes that lasted >= 4 bars
        self.df['squeeze_fired_quality'] = (
            self.df['squeeze_fired'] &
            (pd.Series(duration, index=self.df.index).shift(1) >= 3)
        )

        # Reason: shift by 1 so donchian_high is the PRIOR N-period high
        self.df['donchian_high'] = high.shift(1).rolling(self.donchian_period).max()
        self.df['donchian_low'] = low.shift(1).rolling(self.donchian_period).min()
        self.df['donchian_mid'] = (self.df['donchian_high'] + self.df['donchian_low']) / 2

        # Reason: momentum = close deviation from midpoint, smoothed via linear regression
        midpoint = (self.df['donchian_mid'] + self.df['bb_mid']) / 2
        deviation = close - midpoint
        self.df['squeeze_momentum'] = self._rolling_linreg(deviation, self.momentum_period)
        self.df['squeeze_momentum_prev'] = self.df['squeeze_momentum'].shift(1)

        # Volume confirmation
        self.df['volume_ma'] = volume.rolling(self.volume_ma_period).mean()
        self.df['volume_ratio'] = volume / self.df['volume_ma']

        # Reason: trend filter — configurable SMA for intermediate trend direction
        self.df['sma_50'] = close.rolling(self.trend_sma_period).mean()

        # Reason: ATR expansion filter
        self.df['atr_ma'] = self.df['atr'].rolling(self.trend_sma_period).mean()

        # Reason: RSI for overbought exit — mean reversion layer
        self._compute_rsi(close)

        # Reason: Chandelier Exit — trails from highest high, better for breakouts
        self.df['chandelier_stop'] = (
            high.rolling(self.chandelier_period).max()
            - self.chandelier_mult * self.df['atr']
        )

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicators for the last row.

        Falls back to full calculation when insufficient data.
        """
        self.df = new_df
        n = len(self.df)

        min_required = max(self.bb_period, self.kc_period, self.donchian_period, self.atr_period) + 2
        if n < min_required:
            return self.calculate()

        # Reason: full recalc is still fast for typical bar counts (<10k rows)
        return self.calculate()

    def _compute_rsi(self, close: pd.Series) -> None:
        """Compute RSI(14) using Wilder's smoothing, stored as df['rsi']."""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        n = len(close)

        if n <= self.rsi_period:
            self.df['rsi'] = np.nan
            return

        rsi_values = np.full(n, np.nan)
        gain_arr = gain.values
        loss_arr = loss.values

        avg_gain = np.nanmean(gain_arr[1:self.rsi_period + 1])
        avg_loss = np.nanmean(loss_arr[1:self.rsi_period + 1])
        rsi_values[self.rsi_period] = 100 - 100 / (1 + avg_gain / avg_loss) if avg_loss > 0 else 100.0

        for i in range(self.rsi_period + 1, n):
            avg_gain = (avg_gain * (self.rsi_period - 1) + gain_arr[i]) / self.rsi_period
            avg_loss = (avg_loss * (self.rsi_period - 1) + loss_arr[i]) / self.rsi_period
            rsi_values[i] = 100 - 100 / (1 + avg_gain / avg_loss) if avg_loss > 0 else 100.0

        self.df['rsi'] = rsi_values

    def _rolling_linreg(self, series: pd.Series, period: int) -> pd.Series:
        """Compute rolling linear regression value (last point on the line)."""
        result = pd.Series(np.nan, index=series.index)
        values = series.astype(float).values

        for i in range(period - 1, len(values)):
            window = values[i - period + 1: i + 1]
            if np.any(np.isnan(window)):
                continue
            x = np.arange(period, dtype=float)
            x_mean = x.mean()
            y_mean = window.mean()
            slope = np.sum((x - x_mean) * (window - y_mean)) / np.sum((x - x_mean) ** 2)
            intercept = y_mean - slope * x_mean
            result.iloc[i] = intercept + slope * (period - 1)

        return result

    def _indicator_columns(self) -> list[str]:
        """List of all indicator column names added by this class."""
        return [
            'atr', 'bb_mid', 'bb_upper', 'bb_lower', 'bb_width', 'bbw_percentile',
            'kc_mid', 'kc_upper', 'kc_lower',
            'squeeze_on', 'squeeze_duration', 'squeeze_fired', 'squeeze_fired_quality',
            'donchian_high', 'donchian_low', 'donchian_mid',
            'squeeze_momentum', 'squeeze_momentum_prev',
            'volume_ma', 'volume_ratio', 'sma_50', 'atr_ma',
            'rsi', 'chandelier_stop',
        ]
