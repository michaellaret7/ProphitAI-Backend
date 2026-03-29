"""TTM Squeeze Breakout strategy (v2 — optimized for high Sharpe ratio).

Detects when Bollinger Bands compress inside Keltner Channels (the "squeeze"),
then enters on the breakout when bands expand with momentum, Donchian channel,
and volume confirmation. Uses triple-barrier exits (Chandelier stop, RSI
overbought, Donchian low) for consistent risk-adjusted returns.

Best suited for daily timeframe on liquid US equities.
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.indicators.squeeze_breakout import SqueezeBreakoutIndicator
from prophitai_algo_trading.strategies.squeeze_breakout.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class SqueezeBreakout(BaseStrategy):
    """Volatility squeeze breakout strategy with triple-barrier exits.

    Args:
        bb_period: Bollinger Band SMA period.
        bb_std: Bollinger Band standard deviation multiplier.
        kc_period: Keltner Channel EMA period.
        kc_atr_mult: Keltner Channel ATR multiplier.
        donchian_period: Donchian Channel lookback for breakout levels.
        atr_period: ATR period for volatility measurement.
        momentum_period: Linear regression period for momentum oscillator.
        volume_ma_period: Volume moving average period.
        rsi_period: RSI period for overbought detection.
        chandelier_period: Highest-high lookback for Chandelier exit.
        chandelier_mult: ATR multiplier for Chandelier exit.
        trend_sma_period: SMA period for trend filter (50 for daily, 200 for 15min).
    """

    def __init__(
        self,
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
        trend_sma_period: int = 50,
    ):
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
        self.trend_sma_period = trend_sma_period
        self._indicator: SqueezeBreakoutIndicator | None = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all squeeze breakout indicators on the full DataFrame."""
        if df.empty:
            return df

        self._indicator = SqueezeBreakoutIndicator(
            df,
            bb_period=self.bb_period,
            bb_std=self.bb_std,
            kc_period=self.kc_period,
            kc_atr_mult=self.kc_atr_mult,
            donchian_period=self.donchian_period,
            atr_period=self.atr_period,
            momentum_period=self.momentum_period,
            volume_ma_period=self.volume_ma_period,
            rsi_period=self.rsi_period,
            chandelier_period=self.chandelier_period,
            chandelier_mult=self.chandelier_mult,
            trend_sma_period=self.trend_sma_period,
        )
        return self._indicator.df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update squeeze indicators for the last row."""
        if self._indicator is None:
            return self.calculate_indicators(df)

        return self._indicator.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on squeeze breakout conditions."""
        return {
            "long_entry": long_entry(df),
            "long_exit": long_exit(df),
            "short_entry": short_entry(df),
            "short_exit": short_exit(df),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Momentum magnitude — stronger directional thrust = higher conviction breakout."""
        return df["momentum"].abs()

    @property
    def min_bars_required(self) -> int:
        """Longest lookback: trend SMA + buffer for BB width percentile warmup."""
        return self.trend_sma_period + 30
