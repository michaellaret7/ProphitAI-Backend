from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """Technical indicators not already defined elsewhere in calculations.

    Includes: EMA, WMA, VWAP, Bollinger Bands, Stochastic Oscillator, ATR,
    Donchian Channels, Keltner Channels, Parabolic SAR, ADX, CCI.
    """

    def __init__(self, ohlcv: pd.DataFrame):
        self.df = ohlcv.copy()
        # Expect columns: open, high, low, close, volume
        if not set(["open", "high", "low", "close"]).issubset(self.df.columns):
            raise ValueError("OHLC dataframe must contain open, high, low, close columns")

    # ------------------------ Moving Averages ------------------------ #
    def ema(self, span: int = 20) -> pd.Series:
        return self.df["close"].ewm(span=span, adjust=False).mean()

    def wma(self, window: int = 20) -> pd.Series:
        weights = np.arange(1, window + 1)
        return self.df["close"].rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    def vwap(self, window: int = 20) -> pd.Series:
        if "volume" not in self.df.columns:
            raise ValueError("volume column required for VWAP")
        pv = self.df["close"] * self.df["volume"]
        cum_pv = pv.rolling(window).sum()
        cum_vol = self.df["volume"].rolling(window).sum()
        return cum_pv / cum_vol

    # ------------------------ Bollinger Bands ------------------------ #
    def bollinger_bands(self, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ma = self.df["close"].rolling(window).mean()
        sd = self.df["close"].rolling(window).std(ddof=1)
        upper = ma + num_std * sd
        lower = ma - num_std * sd
        return lower, ma, upper

    # ------------------------ Stochastic Oscillator ------------------------ #
    def stochastic(self, k_window: int = 14, d_window: int = 3) -> Tuple[pd.Series, pd.Series]:
        lowest_low = self.df["low"].rolling(k_window).min()
        highest_high = self.df["high"].rolling(k_window).max()
        percent_k = (self.df["close"] - lowest_low) / (highest_high - lowest_low) * 100
        percent_d = percent_k.rolling(d_window).mean()
        return percent_k, percent_d

    # ------------------------ ATR ------------------------ #
    def atr(self, period: int = 14) -> pd.Series:
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        close_prev = close.shift(1)
        tr = np.maximum(high - low, np.maximum(abs(high - close_prev), abs(low - close_prev)))
        return tr.rolling(window=period).mean()

    # ------------------------ Donchian Channels ------------------------ #
    def donchian(self, window: int = 20) -> Tuple[pd.Series, pd.Series]:
        upper = self.df["high"].rolling(window).max()
        lower = self.df["low"].rolling(window).min()
        return lower, upper

    # ------------------------ Keltner Channels ------------------------ #
    def keltner(self, ema_period: int = 20, atr_period: int = 10, atr_mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema = self.ema(ema_period)
        atr = self.atr(atr_period)
        upper = ema + atr_mult * atr
        lower = ema - atr_mult * atr
        return lower, ema, upper

    # ------------------------ Parabolic SAR ------------------------ #
    def parabolic_sar(self, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
        high = self.df["high"].values
        low = self.df["low"].values
        close = self.df["close"].values
        length = len(close)
        sar = np.zeros(length)
        bull = True
        af = step
        ep = low[0]
        sar[0] = low[0]
        for i in range(1, length):
            prev_sar = sar[i - 1]
            if bull:
                sar[i] = prev_sar + af * (ep - prev_sar)
                sar[i] = min(sar[i], low[i - 1], low[i])
                if close[i] < sar[i]:
                    bull = False
                    sar[i] = ep
                    af = step
                    ep = high[i]
            else:
                sar[i] = prev_sar + af * (ep - prev_sar)
                sar[i] = max(sar[i], high[i - 1], high[i])
                if close[i] > sar[i]:
                    bull = True
                    sar[i] = ep
                    af = step
                    ep = low[i]
            if bull:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + step, max_step)
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + step, max_step)
        return pd.Series(sar, index=self.df.index)

    # ------------------------ ADX ------------------------ #
    def adx(self, period: int = 14) -> pd.Series:
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        plus_dm = high.diff()
        minus_dm = low.diff(-1)
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        tr1 = (high - low)
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.ewm(alpha=1/period, adjust=False).mean()
        return adx

    # ------------------------ CCI ------------------------ #
    def cci(self, period: int = 20) -> pd.Series:
        typical_price = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        sma = typical_price.rolling(period).mean()
        mad = (typical_price - sma).abs().rolling(period).mean()
        cci = (typical_price - sma) / (0.015 * mad)
        return cci

