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

    # -----------------------------
    # Helpers
    # -----------------------------
    @staticmethod
    def _sma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window, min_periods=window).mean()

    @staticmethod
    def _ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _wilder_ma(series: pd.Series, period: int) -> pd.Series:
        # Wilder's smoothing is EMA with alpha = 1/period
        alpha = 1.0 / float(period)
        return series.ewm(alpha=alpha, adjust=False).mean()

    @staticmethod
    def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        prev_close = close.shift(1)
        high_low = high - low
        high_prev_close = (high - prev_close).abs()
        low_prev_close = (low - prev_close).abs()
        tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        return tr

    # -----------------------------
    # Indicators
    # -----------------------------
    def rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index (Wilder)

        RSI = 100 - 100 / (1 + RS), where RS = avg_gain / avg_loss (Wilder MA)
        """
        close = self.df["close"]
        delta = close.diff()
        gains = delta.clip(lower=0.0)
        losses = (-delta.clip(upper=0.0))

        avg_gain = self._wilder_ma(gains, period)
        avg_loss = self._wilder_ma(losses, period)

        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi.name = f"rsi_{period}"
        return rsi

    def stoch(self, k_period: int = 9, d_period: int = 6) -> pd.DataFrame:
        """Stochastic Oscillator (%K and %D).

        %K = 100 * (close - lowest_low) / (highest_high - lowest_low)
        %D = SMA(%K, d_period)
        """
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
        highest_high = high.rolling(window=k_period, min_periods=k_period).max()
        range_hl = (highest_high - lowest_low).replace(0.0, np.nan)

        k = 100.0 * (close - lowest_low) / range_hl
        d = k.rolling(window=d_period, min_periods=d_period).mean()

        out = pd.DataFrame({
            "stoch_k": k,
            "stoch_d": d,
        })
        return out

    def stoch_rsi(self, period: int = 14) -> pd.Series:
        """Stochastic RSI (scaled 0..100).

        StochRSI = 100 * (RSI - min(RSI_n)) / (max(RSI_n) - min(RSI_n))
        """
        rsi_series = self.rsi(period=period)
        min_rsi = rsi_series.rolling(window=period, min_periods=period).min()
        max_rsi = rsi_series.rolling(window=period, min_periods=period).max()
        denom = (max_rsi - min_rsi).replace(0.0, np.nan)
        stoch_rsi = 100.0 * (rsi_series - min_rsi) / denom
        stoch_rsi.name = f"stochrsi_{period}"
        return stoch_rsi

    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """MACD line, Signal line, and Histogram.

        MACD = EMA(fast) - EMA(slow); Signal = EMA(MACD, signal); Hist = MACD - Signal
        """
        close = self.df["close"]
        ema_fast = self._ema(close, fast_period)
        ema_slow = self._ema(close, slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal_period)
        hist = macd_line - signal_line

        out = pd.DataFrame({
            "macd": macd_line,
            "signal": signal_line,
            "hist": hist,
        })
        return out

    def bollinger_bands(self, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """Bollinger Bands (SMA-based).

        Middle = SMA(period)
        Upper = Middle + num_std * rolling_std
        Lower = Middle - num_std * rolling_std
        """
        close = self.df["close"]
        middle = self._sma(close, period)
        rolling_std = close.rolling(window=period, min_periods=period).std(ddof=0)
        upper = middle + num_std * rolling_std
        lower = middle - num_std * rolling_std

        out = pd.DataFrame({
            "bb_middle": middle,
            "bb_upper": upper,
            "bb_lower": lower,
        })
        return out

    def adx(self, period: int = 14) -> pd.DataFrame:
        """Average Directional Index with +DI and -DI (Wilder).

        - Compute +DM and -DM from high/low diffs
        - Smooth +DM, -DM, TR with Wilder MA to get +DI and -DI
        - ADX = Wilder MA of DX = 100 * |+DI - -DI| / (+DI + -DI)
        """
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)

        tr = self._true_range(high, low, close)
        atr = self._wilder_ma(tr, period)

        plus_di = 100.0 * self._wilder_ma(plus_dm, period) / atr.replace(0.0, np.nan)
        minus_di = 100.0 * self._wilder_ma(minus_dm, period) / atr.replace(0.0, np.nan)

        dx = 100.0 * (plus_di.subtract(minus_di).abs()) / (plus_di + minus_di)
        adx = self._wilder_ma(dx, period)

        out = pd.DataFrame({
            "+di": plus_di,
            "-di": minus_di,
            "adx": adx,
        })
        return out

    def williams_r(self, period: int = 14) -> pd.Series:
        """Williams %R (scaled -100..0)."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        highest_high = high.rolling(window=period, min_periods=period).max()
        lowest_low = low.rolling(window=period, min_periods=period).min()
        denom = (highest_high - lowest_low).replace(0.0, np.nan)
        willr = -100.0 * (highest_high - close) / denom
        willr.name = f"williams_r_{period}"
        return willr

    def cci(self, period: int = 14) -> pd.Series:
        """Commodity Channel Index."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        typical_price = (high + low + close) / 3.0
        sma_tp = self._sma(typical_price, period)

        # Mean deviation of typical price from its SMA over the lookback
        mean_dev = (
            typical_price.rolling(window=period, min_periods=period)
            .apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=False)
        )

        cci = (typical_price - sma_tp) / (0.015 * mean_dev.replace(0.0, np.nan))
        cci.name = f"cci_{period}"
        return cci

    def atr(self, period: int = 14) -> pd.Series:
        """Average True Range (Wilder)."""
        tr = self._true_range(self.df["high"], self.df["low"], self.df["close"])
        atr = self._wilder_ma(tr, period)
        atr.name = f"atr_{period}"
        return atr

    def highs_lows(self, period: int = 14) -> pd.DataFrame:
        """Rolling highest high and lowest low over the lookback window."""
        high = self.df["high"]
        low = self.df["low"]
        hh = high.rolling(window=period, min_periods=period).max()
        ll = low.rolling(window=period, min_periods=period).min()
        out = pd.DataFrame({"rolling_high": hh, "rolling_low": ll})
        return out

    def ultimate_oscillator(self, short: int = 7, medium: int = 14, long: int = 28) -> pd.Series:
        """Ultimate Oscillator (default 7/14/28 weighting 4:2:1)."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        prev_close = close.shift(1)

        buying_pressure = close - pd.concat([low, prev_close], axis=1).min(axis=1)
        true_range = pd.concat([high, prev_close], axis=1).max(axis=1) - pd.concat([low, prev_close], axis=1).min(axis=1)

        avg_bp_short = buying_pressure.rolling(window=short, min_periods=short).sum()
        avg_tr_short = true_range.rolling(window=short, min_periods=short).sum()
        avg_bp_med = buying_pressure.rolling(window=medium, min_periods=medium).sum()
        avg_tr_med = true_range.rolling(window=medium, min_periods=medium).sum()
        avg_bp_long = buying_pressure.rolling(window=long, min_periods=long).sum()
        avg_tr_long = true_range.rolling(window=long, min_periods=long).sum()

        uo = 100.0 * (
            4.0 * (avg_bp_short / avg_tr_short.replace(0.0, np.nan))
            + 2.0 * (avg_bp_med / avg_tr_med.replace(0.0, np.nan))
            + 1.0 * (avg_bp_long / avg_tr_long.replace(0.0, np.nan))
        ) / 7.0
        uo.name = "ultimate_oscillator"
        return uo

    def roc(self, period: int = 10) -> pd.Series:
        """Rate of Change (%)."""
        close = self.df["close"]
        roc = 100.0 * (close / close.shift(period) - 1.0)
        roc.name = f"roc_{period}"
        return roc

    def bull_bear_power(self, period: int = 13) -> pd.DataFrame:
        """Elder's Bull and Bear Power using EMA(period)."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        ema = self._ema(close, period)
        bull = high - ema
        bear = low - ema
        out = pd.DataFrame({"bull_power": bull, "bear_power": bear})
        return out

    def vwap(self) -> pd.Series:
        """Volume Weighted Average Price using typical price.

        vwap = cumsum(typical_price * volume) / cumsum(volume)
        typical_price = (high + low + close) / 3
        """
        if "volume" not in self.df.columns:
            raise ValueError("VWAP requires 'volume' column in dataframe")
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        volume = self.df["volume"]
        typical_price = (high + low + close) / 3.0
        cum_tpv = (typical_price * volume).cumsum()
        cum_vol = volume.cumsum().replace(0.0, np.nan)
        vwap = cum_tpv / cum_vol
        vwap.name = "vwap"
        return vwap

    def donchian_channels(self, period: int = 20) -> pd.DataFrame:
        """Donchian Channels over lookback period.

        upper = rolling max(high), lower = rolling min(low), middle = (upper + lower)/2
        """
        high = self.df["high"]
        low = self.df["low"]
        upper = high.rolling(window=period, min_periods=period).max()
        lower = low.rolling(window=period, min_periods=period).min()
        middle = (upper + lower) / 2.0
        out = pd.DataFrame({
            "donchian_upper": upper,
            "donchian_middle": middle,
            "donchian_lower": lower,
        })
        return out

    def keltner_channels(self, period: int = 20, atr_period: int | None = None, multiplier: float = 2.0) -> pd.DataFrame:
        """Keltner Channels using EMA and ATR.

        middle = EMA(close, period)
        upper = middle + multiplier * ATR(atr_period or period)
        lower = middle - multiplier * ATR(atr_period or period)
        """
        if atr_period is None:
            atr_period = period
        close = self.df["close"]
        middle = self._ema(close, period)
        atr_vals = self.atr(atr_period)
        upper = middle + multiplier * atr_vals
        lower = middle - multiplier * atr_vals
        out = pd.DataFrame({
            "keltner_middle": middle,
            "keltner_upper": upper,
            "keltner_lower": lower,
        })
        return out

    def parabolic_sar(self, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
        """Parabolic SAR implementation (PSAR).

        step: acceleration factor increment (default 0.02)
        max_step: maximum acceleration factor (default 0.2)
        Returns a Series named 'psar'.
        """
        high = self.df["high"].to_numpy()
        low = self.df["low"].to_numpy()
        close = self.df["close"].to_numpy()
        n = len(close)
        psar = np.full(n, np.nan, dtype=float)
        if n == 0:
            return pd.Series(psar, index=self.df.index, name="psar")
        if n < 3:
            # Not enough data to compute SAR reliably
            return pd.Series(psar, index=self.df.index, name="psar")

        # Initialize trend based on first two closes
        uptrend = close[1] > close[0]
        ep = high[0] if uptrend else low[0]
        af = step
        psar[1] = low[0] if uptrend else high[0]

        for i in range(2, n):
            prev_psar = psar[i - 1]
            if np.isnan(prev_psar):
                prev_psar = low[i - 1] if uptrend else high[i - 1]
            psar[i] = prev_psar + af * (ep - prev_psar)

            if uptrend:
                # Clamp to recent lows
                psar[i] = min(psar[i], low[i - 1], low[i - 2])
                # New extreme point?
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + step, max_step)
                # Trend reversal?
                if low[i] < psar[i]:
                    uptrend = False
                    psar[i] = ep
                    ep = low[i]
                    af = step
            else:
                # Clamp to recent highs
                psar[i] = max(psar[i], high[i - 1], high[i - 2])
                # New extreme point?
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + step, max_step)
                # Trend reversal?
                if high[i] > psar[i]:
                    uptrend = True
                    psar[i] = ep
                    ep = high[i]
                    af = step

        return pd.Series(psar, index=self.df.index, name="psar")

    def moving_averages(self, lookbacks: list[int], ma_type: str = "sma", price_col: str = "close") -> pd.DataFrame:
        """Compute moving averages for arbitrary lookbacks.

        - ma_type: "sma" | "ema" | "wilder"
        - price_col: column to average (default "close")
        Returns a DataFrame with one column per lookback, named like "sma_20".
        """
        if price_col not in self.df.columns:
            raise ValueError(f"price_col '{price_col}' not found in DataFrame columns")
        if not lookbacks:
            raise ValueError("lookbacks must be a non-empty list of positive integers")

        series = self.df[price_col]
        outputs: dict[str, pd.Series] = {}

        for lb in lookbacks:
            if not isinstance(lb, int) or lb <= 0:
                raise ValueError("lookbacks must contain positive integers")
            if ma_type == "sma":
                ma = self._sma(series, lb)
            elif ma_type == "ema":
                ma = self._ema(series, lb)
            elif ma_type == "wilder":
                ma = self._wilder_ma(series, lb)
            else:
                raise ValueError("ma_type must be one of: 'sma', 'ema', 'wilder'")
            outputs[f"{ma_type}_{lb}"] = ma

        return pd.DataFrame(outputs)


