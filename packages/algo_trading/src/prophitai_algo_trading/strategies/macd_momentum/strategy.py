"""MACD Momentum Crossover strategy for trend-following via momentum reversals.

Uses MACD (12, 26, 9) to detect momentum shifts. Enters long when MACD
crosses above signal from below zero (bullish reversal), enters short when
MACD crosses below signal from above zero (bearish reversal). Exits on the
opposite crossover.

Works well on daily and intraday timeframes. Default parameters (12/26/9)
are the institutional standard used across most quantitative trading desks.
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.indicators.macd import MACD
from prophitai_algo_trading.strategies.macd_momentum.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class MACDMomentum(BaseStrategy):
    """Momentum strategy using MACD crossovers with zero-line filter.

    Args:
        fast_period: Fast EMA period.
        slow_period: Slow EMA period.
        signal_period: Signal line EMA period.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self._macd_calc: MACD | None = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute MACD indicators on the full DataFrame."""
        if df.empty:
            return df

        self._macd_calc = MACD(
            df,
            fast_period=self.fast_period,
            slow_period=self.slow_period,
            signal_period=self.signal_period,
        )
        return self._macd_calc.df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update MACD indicators for the last row."""
        if self._macd_calc is None:
            return self.calculate_indicators(df)

        return self._macd_calc.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on MACD crossover conditions."""
        return {
            "long_entry": long_entry(df),
            "long_exit": long_exit(df),
            "short_entry": short_entry(df),
            "short_exit": short_exit(df),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """MACD histogram magnitude — larger divergence = stronger momentum signal."""
        return df["macd_histogram"].abs()

    @property
    def min_bars_required(self) -> int:
        """Slow EMA + signal period needs the longest lookback."""
        return self.slow_period + self.signal_period
