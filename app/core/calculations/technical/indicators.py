"""Technical Indicators - Main facade class for all technical indicators.

This class provides a unified interface to all technical indicators organized by category.
All calculation logic resides in category-specific modules (momentum, trend, volatility, etc.).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .indicator_calcs import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_bull_bear_power,
    calculate_cci,
    calculate_chaikin_money_flow,
    calculate_donchian_channels,
    calculate_fibonacci_extensions,
    calculate_fibonacci_retracements,
    calculate_highs_lows,
    calculate_ichimoku_cloud,
    calculate_keltner_channels,
    calculate_macd,
    calculate_mfi,
    calculate_moving_averages,
    calculate_obv,
    calculate_parabolic_sar,
    calculate_roc,
    calculate_rsi,
    calculate_stoch,
    calculate_stoch_rsi,
    calculate_supertrend,
    calculate_td_countdown,
    calculate_td_sequential,
    calculate_td_setup,
    calculate_ultimate_oscillator,
    calculate_vwap,
    calculate_williams_r,
)


class TechnicalIndicators:
    """Technical indicators facade providing access to all indicator calculations.

    Momentum Indicators: RSI, Stochastic, Stochastic RSI, MACD, Williams %R, CCI,
    ROC, Ultimate Oscillator, MFI (Money Flow Index), TD Sequential

    Trend Indicators: ADX, Parabolic SAR, Bull/Bear Power, Supertrend

    Volatility/Channel Indicators: ATR, Bollinger Bands, Donchian Channels,
    Keltner Channels, Ichimoku Cloud

    Volume Indicators: VWAP, OBV (On Balance Volume), CMF (Chaikin Money Flow)

    Support/Resistance: Fibonacci Retracements, Fibonacci Extensions

    Moving Averages: SMA, EMA, Wilder MA (flexible periods)
    """

    def __init__(self, ohlcv: pd.DataFrame):
        """Initialize with OHLCV dataframe.

        Args:
            ohlcv: DataFrame with columns: open, high, low, close, volume (optional)
        """
        self.df = ohlcv.copy()
        # Expect columns: open, high, low, close, volume
        if not set(["open", "high", "low", "close"]).issubset(self.df.columns):
            raise ValueError("OHLC dataframe must contain open, high, low, close columns")

    # -----------------------------
    # Momentum Indicators
    # -----------------------------
    def rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index (Wilder)."""
        return calculate_rsi(self.df, period)

    def stoch(self, k_period: int = 9, d_period: int = 6) -> pd.DataFrame:
        """Stochastic Oscillator (%K and %D)."""
        return calculate_stoch(self.df, k_period, d_period)

    def stoch_rsi(self, period: int = 14) -> pd.Series:
        """Stochastic RSI (scaled 0..100)."""
        return calculate_stoch_rsi(self.df, period)

    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """MACD line, Signal line, and Histogram."""
        return calculate_macd(self.df, fast_period, slow_period, signal_period)

    def williams_r(self, period: int = 14) -> pd.Series:
        """Williams %R (scaled -100..0)."""
        return calculate_williams_r(self.df, period)

    def cci(self, period: int = 14) -> pd.Series:
        """Commodity Channel Index."""
        return calculate_cci(self.df, period)

    def roc(self, period: int = 10) -> pd.Series:
        """Rate of Change (%)."""
        return calculate_roc(self.df, period)

    def ultimate_oscillator(self, short: int = 7, medium: int = 14, long: int = 28) -> pd.Series:
        """Ultimate Oscillator (default 7/14/28 weighting 4:2:1)."""
        return calculate_ultimate_oscillator(self.df, short, medium, long)

    def mfi(self, period: int = 14) -> pd.Series:
        """Money Flow Index (MFI) - Volume-weighted RSI."""
        return calculate_mfi(self.df, period)

    def td_setup(self) -> pd.DataFrame:
        """TD Setup - DeMark's 9-count setup phase for trend exhaustion."""
        return calculate_td_setup(self.df)

    def td_countdown(self) -> pd.DataFrame:
        """TD Countdown - DeMark's 13-count countdown phase (non-consecutive)."""
        return calculate_td_countdown(self.df)

    def td_sequential(self) -> pd.DataFrame:
        """TD Sequential - Complete DeMark Sequential indicator (Setup + Countdown)."""
        return calculate_td_sequential(self.df)

    # -----------------------------
    # Trend Indicators
    # -----------------------------
    def adx(self, period: int = 14) -> pd.DataFrame:
        """Average Directional Index with +DI and -DI (Wilder)."""
        return calculate_adx(self.df, period)

    def parabolic_sar(self, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
        """Parabolic SAR implementation (PSAR)."""
        return calculate_parabolic_sar(self.df, step, max_step)

    def bull_bear_power(self, period: int = 13) -> pd.DataFrame:
        """Elder's Bull and Bear Power using EMA(period)."""
        return calculate_bull_bear_power(self.df, period)

    def supertrend(self, atr_period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """Supertrend - Trend-following indicator based on ATR."""
        return calculate_supertrend(self.df, atr_period, multiplier)

    # -----------------------------
    # Volatility/Channel Indicators
    # -----------------------------
    def atr(self, period: int = 14) -> pd.Series:
        """Average True Range (Wilder)."""
        return calculate_atr(self.df, period)

    def bollinger_bands(self, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """Bollinger Bands (SMA-based)."""
        return calculate_bollinger_bands(self.df, period, num_std)

    def donchian_channels(self, period: int = 20) -> pd.DataFrame:
        """Donchian Channels over lookback period."""
        return calculate_donchian_channels(self.df, period)

    def keltner_channels(
        self, period: int = 20, atr_period: int | None = None, multiplier: float = 2.0
    ) -> pd.DataFrame:
        """Keltner Channels using EMA and ATR."""
        return calculate_keltner_channels(self.df, period, atr_period, multiplier)

    def ichimoku_cloud(
        self,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        displacement: int = 26,
    ) -> pd.DataFrame:
        """Ichimoku Cloud - Comprehensive Japanese indicator system."""
        return calculate_ichimoku_cloud(self.df, tenkan_period, kijun_period, senkou_b_period, displacement)

    def highs_lows(self, period: int = 14) -> pd.DataFrame:
        """Rolling highest high and lowest low over the lookback window."""
        return calculate_highs_lows(self.df, period)

    # -----------------------------
    # Volume Indicators
    # -----------------------------
    def vwap(self) -> pd.Series:
        """Volume Weighted Average Price using typical price."""
        return calculate_vwap(self.df)

    def obv(self) -> pd.Series:
        """On Balance Volume (OBV) - Cumulative volume-based momentum indicator."""
        return calculate_obv(self.df)

    def chaikin_money_flow(self, period: int = 21) -> pd.Series:
        """Chaikin Money Flow (CMF) - Measures buying/selling pressure."""
        return calculate_chaikin_money_flow(self.df, period)

    # -----------------------------
    # Support/Resistance
    # -----------------------------
    def fibonacci_retracements(
        self, lookback: Optional[int] = None, start_idx: Optional[int] = None, end_idx: Optional[int] = None
    ) -> dict[str, float]:
        """Calculate Fibonacci retracement levels."""
        return calculate_fibonacci_retracements(self.df, lookback, start_idx, end_idx)

    def fibonacci_extensions(self, start_idx: int, end_idx: int, retrace_idx: int) -> dict[str, float]:
        """Calculate Fibonacci extension levels."""
        return calculate_fibonacci_extensions(self.df, start_idx, end_idx, retrace_idx)

    # -----------------------------
    # Moving Averages
    # -----------------------------
    def moving_averages(self, lookbacks: list[int], ma_type: str = "sma", price_col: str = "close") -> pd.DataFrame:
        """Compute moving averages for arbitrary lookbacks."""
        return calculate_moving_averages(self.df, lookbacks, ma_type, price_col)
