"""Opening Range Breakout (ORB) indicator suite for 15-minute bars.

Captures the high/low of the first 15-minute bar after market open (9:30 ET),
then tracks breakouts, ATR-based stops, and supporting filters.

Components:
- Opening Range: High/Low of the first 15min bar each day
- Range Height: Distance between OR high and OR low for target calculation
- ATR(14): For stop sizing and volatility filtering
- Chandelier Stop: Intraday high - N*ATR for trailing stop
- EMA(20): Trend direction filter
- VWAP: Intraday volume-weighted average price for directional bias
- Volume Ratio: Current bar volume vs 20-bar average for breakout confirmation
- Profit Targets: OR level + N * OR range for take-profit
- Time Filter: Boolean for valid trading hours (avoid lunch chop)
"""

import numpy as np
import pandas as pd

from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class ORBIndicator:
    """Opening Range Breakout indicator with 15-minute bar support.

    Args:
        df: DataFrame with OHLCV columns, datetime-indexed.
        atr_period: ATR lookback period.
        ema_fast: Fast EMA period for trend confirmation.
        ema_slow: Slow EMA period for trend filter.
        volume_ma_period: Volume moving average lookback.
        or_atr_filter: Minimum ATR multiplier for OR height qualification.
        chandelier_mult: ATR multiplier for chandelier trailing stop.
        profit_target_mult: OR range multiplier for profit target.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        atr_period: int = 14,
        ema_fast: int = 9,
        ema_slow: int = 20,
        volume_ma_period: int = 20,
        or_atr_filter: float = 0.5,
        chandelier_mult: float = 2.0,
        profit_target_mult: float = 1.5,
    ):
        self.df = normalize_columns(df.copy())
        self.atr_period = atr_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volume_ma_period = volume_ma_period
        self.or_atr_filter = or_atr_filter
        self.chandelier_mult = chandelier_mult
        self.profit_target_mult = profit_target_mult
        self.calculate()

    def calculate(self) -> pd.DataFrame:
        """Compute all ORB indicators for all rows."""
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        volume = self.df['volume']
        n = len(self.df)

        if n < self.ema_slow + 2:
            for col in self._indicator_columns():
                self.df[col] = np.nan
            return self.df

        # Reason: ATR for stop sizing and volatility filtering
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        self.df['atr'] = tr.rolling(self.atr_period).mean()

        # Reason: EMAs for trend filtering and trailing stops
        self.df['ema_fast'] = close.ewm(span=self.ema_fast, adjust=False).mean()
        self.df['ema_slow'] = close.ewm(span=self.ema_slow, adjust=False).mean()

        # Reason: volume confirmation — breakouts on thin volume fail more often
        self.df['volume_ma'] = volume.rolling(self.volume_ma_period).mean()
        self.df['volume_ratio'] = volume / self.df['volume_ma'].replace(0, np.nan)

        # Reason: VWAP for intraday directional bias
        self._compute_vwap()

        # Reason: identify the opening range bar (first bar of each trading day)
        self._compute_opening_range()

        # Reason: chandelier trailing stop tracks intraday high/low
        self._compute_chandelier_stops()

        # Reason: profit targets based on OR range multiples
        self._compute_profit_targets()

        # Reason: bars_since_open needed by time filter, compute first
        self._compute_bars_since_open()

        # Reason: time-of-day filter uses bars_since_open (timezone-agnostic)
        self._compute_time_filter()

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicators for the last row."""
        self.df = new_df
        return self.calculate()

    def _compute_vwap(self) -> None:
        """Compute intraday VWAP, resetting each trading day."""
        idx = self.df.index
        dates = idx.date
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        tp_vol = typical_price * self.df['volume']

        vwap = np.full(len(self.df), np.nan)
        cum_tp_vol = 0.0
        cum_vol = 0.0
        prev_date = None

        for i in range(len(self.df)):
            current_date = dates[i]
            if current_date != prev_date:
                cum_tp_vol = 0.0
                cum_vol = 0.0
                prev_date = current_date

            cum_tp_vol += tp_vol.iloc[i]
            cum_vol += self.df['volume'].iloc[i]

            if cum_vol > 0:
                vwap[i] = cum_tp_vol / cum_vol

        self.df['vwap'] = vwap

    def _compute_opening_range(self) -> None:
        """Identify first bar of each trading day and propagate OR levels."""
        idx = self.df.index
        dates = idx.date
        n = len(self.df)

        or_high = np.full(n, np.nan)
        or_low = np.full(n, np.nan)
        or_range = np.full(n, np.nan)
        is_or_bar = np.zeros(n, dtype=bool)
        or_valid = np.zeros(n, dtype=bool)

        prev_date = None
        day_or_high = np.nan
        day_or_low = np.nan
        day_or_range_val = np.nan
        day_atr_at_open = np.nan

        for i in range(n):
            current_date = dates[i]
            if current_date != prev_date:
                # Reason: first bar of the day defines the opening range
                day_or_high = self.df['high'].iloc[i]
                day_or_low = self.df['low'].iloc[i]
                day_or_range_val = day_or_high - day_or_low
                is_or_bar[i] = True
                day_atr_at_open = self.df['atr'].iloc[i] if not np.isnan(self.df['atr'].iloc[i]) else 0.0
                prev_date = current_date

            or_high[i] = day_or_high
            or_low[i] = day_or_low
            or_range[i] = day_or_range_val

            # Reason: filter out tiny opening ranges (noise, not real setups)
            if day_atr_at_open > 0 and day_or_range_val >= self.or_atr_filter * day_atr_at_open:
                or_valid[i] = True

        self.df['or_high'] = or_high
        self.df['or_low'] = or_low
        self.df['or_range'] = or_range
        self.df['is_or_bar'] = is_or_bar
        self.df['or_valid'] = or_valid

    def _compute_chandelier_stops(self) -> None:
        """Compute intraday chandelier trailing stops.

        For longs: intraday running high - chandelier_mult * ATR
        For shorts: intraday running low + chandelier_mult * ATR
        Resets each trading day.
        """
        idx = self.df.index
        dates = idx.date
        n = len(self.df)

        intraday_high = np.full(n, np.nan)
        intraday_low = np.full(n, np.nan)
        chandelier_long = np.full(n, np.nan)
        chandelier_short = np.full(n, np.nan)

        prev_date = None
        running_high = np.nan
        running_low = np.nan

        for i in range(n):
            current_date = dates[i]
            h = self.df['high'].iloc[i]
            lo = self.df['low'].iloc[i]
            atr_val = self.df['atr'].iloc[i]

            if current_date != prev_date:
                running_high = h
                running_low = lo
                prev_date = current_date
            else:
                running_high = max(running_high, h)
                running_low = min(running_low, lo)

            intraday_high[i] = running_high
            intraday_low[i] = running_low

            if not np.isnan(atr_val):
                chandelier_long[i] = running_high - self.chandelier_mult * atr_val
                chandelier_short[i] = running_low + self.chandelier_mult * atr_val

        self.df['intraday_high'] = intraday_high
        self.df['intraday_low'] = intraday_low
        self.df['chandelier_long_stop'] = chandelier_long
        self.df['chandelier_short_stop'] = chandelier_short

    def _compute_profit_targets(self) -> None:
        """Compute profit targets based on OR range multiples."""
        self.df['profit_target_long'] = (
            self.df['or_high'] + self.profit_target_mult * self.df['or_range']
        )
        self.df['profit_target_short'] = (
            self.df['or_low'] - self.profit_target_mult * self.df['or_range']
        )

    def _compute_time_filter(self) -> None:
        """Mark valid trading hours using bars_since_open (timezone-agnostic).

        For 15min bars with 26 bars/day:
        - Bar 0: opening bar (OR definition, no trading)
        - Bars 1-7: morning session (9:45-11:15 ET)
        - Bars 8-17: midday (avoid — lunch chop)
        - Bars 18-23: afternoon session (14:00-15:15 ET)
        - Bars 24+: near close (exit positions)
        """
        bso = self.df['bars_since_open']

        # Reason: use bar count instead of clock time to avoid UTC/ET confusion
        # Morning session only (bars 1-10): strongest ORB alpha window
        self.df['time_ok'] = (bso >= 1) & (bso <= 10)

        # Reason: force exit in the last 2 bars of the day
        self.df['near_close'] = bso >= 24

    def _compute_bars_since_open(self) -> None:
        """Count bars since market open for each day."""
        idx = self.df.index
        dates = idx.date
        n = len(self.df)

        bars_since_open = np.zeros(n, dtype=int)
        prev_date = None
        count = 0

        for i in range(n):
            current_date = dates[i]
            if current_date != prev_date:
                count = 0
                prev_date = current_date
            bars_since_open[i] = count
            count += 1

        self.df['bars_since_open'] = bars_since_open

    def _indicator_columns(self) -> list[str]:
        """List of all indicator column names added by this class."""
        return [
            'atr', 'ema_fast', 'ema_slow', 'volume_ma', 'volume_ratio',
            'vwap', 'or_high', 'or_low', 'or_range', 'is_or_bar', 'or_valid',
            'intraday_high', 'intraday_low',
            'chandelier_long_stop', 'chandelier_short_stop',
            'profit_target_long', 'profit_target_short',
            'time_ok', 'near_close', 'bars_since_open',
        ]
