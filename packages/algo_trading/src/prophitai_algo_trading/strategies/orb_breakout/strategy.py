"""Opening Range Breakout (ORB) strategy for 15-minute bars.

Captures the high/low of the first 15-minute bar after market open,
enters on confirmed breakouts with VWAP and volume filters, and
exits via EMA trailing stops or time-based exit before close.

Academically validated approach (Zarattini et al., 2024) achieving
Sharpe > 2 on "Stocks in Play" — adapted here for a general liquid
equity universe with additional filters to reduce false breakouts.
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.indicators.orb import ORBIndicator
from prophitai_algo_trading.strategies.orb_breakout.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class ORBBreakout(BaseStrategy):
    """Opening Range Breakout strategy for 15-minute intraday bars.

    Args:
        atr_period: ATR lookback for volatility measurement.
        ema_fast: Fast EMA for trend confirmation.
        ema_slow: Slow EMA for trend filter.
        volume_ma_period: Volume moving average lookback.
        or_atr_filter: Min OR height as fraction of ATR (filters tiny ranges).
        chandelier_mult: ATR multiplier for chandelier trailing stop.
        profit_target_mult: OR range multiplier for profit target.
    """

    def __init__(
        self,
        atr_period: int = 14,
        ema_fast: int = 9,
        ema_slow: int = 20,
        volume_ma_period: int = 20,
        or_atr_filter: float = 0.3,
        chandelier_mult: float = 4.5,
        profit_target_mult: float = 2.0,
    ):
        self.atr_period = atr_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volume_ma_period = volume_ma_period
        self.or_atr_filter = or_atr_filter
        self.chandelier_mult = chandelier_mult
        self.profit_target_mult = profit_target_mult
        self._indicator: ORBIndicator | None = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all ORB indicators on the full DataFrame."""
        if df.empty:
            return df

        self._indicator = ORBIndicator(
            df,
            atr_period=self.atr_period,
            ema_fast=self.ema_fast,
            ema_slow=self.ema_slow,
            volume_ma_period=self.volume_ma_period,
            or_atr_filter=self.or_atr_filter,
            chandelier_mult=self.chandelier_mult,
            profit_target_mult=self.profit_target_mult,
        )
        return self._indicator.df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update ORB indicators for the last row."""
        if self._indicator is None:
            return self.calculate_indicators(df)

        return self._indicator.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on ORB conditions."""
        return {
            "long_entry": long_entry(df),
            "long_exit": long_exit(df),
            "short_entry": short_entry(df),
            "short_exit": short_exit(df),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Volume ratio — stronger volume confirmation = higher conviction breakout."""
        return df["volume_ratio"]

    @property
    def min_bars_required(self) -> int:
        """EMA slow + ATR period gives sufficient warmup."""
        return self.ema_slow + self.atr_period
