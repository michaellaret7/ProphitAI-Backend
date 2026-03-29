"""Kalman Filter Adaptive Trend/Mean-Reversion strategy.

Uses a Local Linear Trend Kalman filter to estimate dynamic fair value
and trend slope.  Adaptively trades mean-reversion when the price tracks
the model (low innovation variance) and momentum when the price deviates
(high innovation variance).

Recommended warmup_bars: 150 (covers regime_window + rolling std convergence).
Default data_interval: 1day (works on any timeframe, but daily is most studied).
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.indicators.kalman_filter import KalmanFilter
from prophitai_algo_trading.strategies.kalman_stat_arb.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class KalmanStatArb(BaseStrategy):
    """Kalman Filter adaptive trend/mean-reversion strategy.

    Args:
        q_level: Process noise variance for level state.
        q_slope: Process noise variance for slope state.
        r_noise: Measurement noise variance.
        z_entry: Z-score threshold for mean-reversion entry.
        z_exit: Z-score threshold for mean-reversion exit.
        spread_window: Rolling window for z-score std and slope SMA.
        regime_window: Rolling window for regime detection.
        regime_percentile: Innovation variance percentile for regime threshold.
    """

    def __init__(
        self,
        q_level: float = 1e-5,
        q_slope: float = 1e-7,
        r_noise: float = 1.0,
        z_entry: float = 2.0,
        z_exit: float = 0.5,
        spread_window: int = 50,
        regime_window: int = 100,
        regime_percentile: float = 70.0,
    ):
        self.q_level = q_level
        self.q_slope = q_slope
        self.r_noise = r_noise
        self.z_entry = z_entry
        self.z_exit = z_exit
        self.spread_window = spread_window
        self.regime_window = regime_window
        self.regime_percentile = regime_percentile
        self._kalman_calc: KalmanFilter | None = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute Kalman filter outputs on the full DataFrame."""
        if df.empty:
            return df

        self._kalman_calc = KalmanFilter(
            df,
            q_level=self.q_level,
            q_slope=self.q_slope,
            r_noise=self.r_noise,
            spread_window=self.spread_window,
            regime_window=self.regime_window,
            regime_percentile=self.regime_percentile,
        )
        return self._kalman_calc.df

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update Kalman filter outputs for the last row."""
        if self._kalman_calc is None:
            return self.calculate_indicators(df)

        return self._kalman_calc.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on Kalman regime-adaptive logic."""
        return {
            "long_entry": long_entry(df, self.z_entry),
            "long_exit": long_exit(df, self.z_exit),
            "short_entry": short_entry(df, self.z_entry),
            "short_exit": short_exit(df, self.z_exit),
        }

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Kalman z-score magnitude — larger deviation = stronger stat-arb signal."""
        return df["kalman_z_score"].abs()

    @property
    def min_bars_required(self) -> int:
        """Regime window is the longest lookback needed."""
        return self.regime_window + self.spread_window
