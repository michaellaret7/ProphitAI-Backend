"""Ichimoku Cloud trend-following strategy.

Enters long when Tenkan crosses above Kijun while price is above cloud,
enters short when Tenkan crosses below Kijun while price is below cloud.
Exits when price crosses the cloud boundary.
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.indicators.ichimoku_cloud import IchimokuCloud
from prophitai_algo_trading.strategies.ichimoku_cross.trade_logic import (
    ichimoku_long_entry,
    ichimoku_long_exit,
    ichimoku_short_entry,
    ichimoku_short_exit,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class IchimokuCross(BaseStrategy):
    """Ichimoku Cloud crossover strategy.

    Args:
        tenkan_period: Tenkan-sen (conversion line) period.
        kijun_period: Kijun-sen (base line) period.
        senkou_b_period: Senkou Span B period.
    """

    def __init__(
        self,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
    ):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self._ichimoku: IchimokuCloud | None = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Ichimoku Cloud indicators on the full DataFrame."""
        if df.empty:
            return df

        self._ichimoku = IchimokuCloud(df)
        df = self._ichimoku.calculate()
        return df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update Ichimoku indicators for the last row."""
        if self._ichimoku is None:
            return self.calculate_indicators(df)

        return self._ichimoku.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on Ichimoku conditions."""
        return {
            "long_entry": ichimoku_long_entry(df),
            "long_exit": ichimoku_long_exit(df),
            "short_entry": ichimoku_short_entry(df),
            "short_exit": ichimoku_short_exit(df),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Tenkan-Kijun separation — wider spread = stronger trend signal."""
        return (df["tenkan"] - df["kijun"]).abs()

    @property
    def min_bars_required(self) -> int:
        """Senkou Span B needs the longest lookback."""
        return self.senkou_b_period
