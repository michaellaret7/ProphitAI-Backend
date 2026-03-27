"""Kalman Filter indicator using a Local Linear Trend state-space model.

Estimates dynamic fair value (level) and trend (slope) via Bayesian
recursive updating.  Produces spread, z-score, innovation variance,
and a binary regime label (mean-reverting vs trending).

Supports both full batch calculation and efficient incremental updates
for real-time bar-by-bar processing.
"""

import numpy as np
import pandas as pd

from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class KalmanFilter:
    """Local Linear Trend Kalman filter with regime detection.

    State vector: x = [level, slope]
    Transition:   x_t = F @ x_{t-1} + process_noise
    Observation:  y_t = H @ x_t + measurement_noise

    Args:
        df: DataFrame with 'close' column.
        q_level: Process noise variance for the level state.
        q_slope: Process noise variance for the slope state.
        r_noise: Measurement noise variance.
        spread_window: Rolling window for z-score std and slope SMA.
        regime_window: Rolling window for innovation variance percentile.
        regime_percentile: Percentile threshold — above = trending regime.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        q_level: float = 1e-5,
        q_slope: float = 1e-7,
        r_noise: float = 1.0,
        spread_window: int = 50,
        regime_window: int = 100,
        regime_percentile: float = 70.0,
    ):
        self.df = normalize_columns(df.copy())
        self.q_level = q_level
        self.q_slope = q_slope
        self.r_noise = r_noise
        self.spread_window = spread_window
        self.regime_window = regime_window
        self.regime_percentile = regime_percentile

        # Kalman state — persisted between incremental updates
        self.x: np.ndarray | None = None  # shape (2,)
        self.P: np.ndarray | None = None  # shape (2, 2)

        self.calculate()

    # ================================
    # --> Helper funcs
    # ================================

    def _predict(self) -> tuple[np.ndarray, np.ndarray]:
        """Kalman predict step.  Returns (x_pred, P_pred)."""
        F = np.array([[1.0, 1.0], [0.0, 1.0]])
        Q = np.array([[self.q_level, 0.0], [0.0, self.q_slope]])
        x_pred = F @ self.x
        P_pred = F @ self.P @ F.T + Q
        return x_pred, P_pred

    def _update(
        self, x_pred: np.ndarray, P_pred: np.ndarray, close: float
    ) -> tuple[float, float]:
        """Kalman update step.  Returns (innovation, innovation_variance).

        Mutates self.x and self.P in-place.
        """
        # Reason: H = [1, 0] so H @ P_pred @ H.T simplifies to P_pred[0, 0]
        predicted_obs = x_pred[0]
        innovation = close - predicted_obs
        S = P_pred[0, 0] + self.r_noise  # innovation variance

        # Kalman gain: K = P_pred @ H.T / S  →  P_pred[:, 0] / S
        K = P_pred[:, 0] / S

        self.x = x_pred + K * innovation
        # Reason: Joseph form is more numerically stable but for 2x2 the
        # standard form (I - K @ H) @ P_pred is sufficient
        I_KH = np.eye(2)
        I_KH[:, 0] -= K
        self.P = I_KH @ P_pred

        return innovation, S

    def _compute_derived_columns(self) -> None:
        """Compute spread, z-score, slope SMA, and regime from raw Kalman outputs."""
        self.df['kalman_spread'] = self.df['close'] - self.df['kalman_level']

        # Reason: replace zero std with NaN to avoid inf z-scores on flat stretches
        rolling_std = self.df['kalman_spread'].rolling(self.spread_window).std()
        rolling_std = rolling_std.replace(0, np.nan)
        self.df['kalman_z_score'] = self.df['kalman_spread'] / rolling_std

        self.df['kalman_slope_sma'] = (
            self.df['kalman_slope'].rolling(self.spread_window).mean()
        )

        # Regime: 1 = trending (high innovation variance), 0 = mean-reverting
        rolling_threshold = (
            self.df['kalman_innov_var']
            .rolling(self.regime_window)
            .quantile(self.regime_percentile / 100.0)
        )
        self.df['kalman_regime'] = (
            (self.df['kalman_innov_var'] > rolling_threshold).astype(float)
        )
        # Reason: default NaN regime to mean-reverting (safer assumption)
        self.df['kalman_regime'] = self.df['kalman_regime'].fillna(0).astype(int)

    def calculate(self) -> pd.DataFrame:
        """Full batch forward pass of the Kalman filter over all rows."""
        close = self.df['close'].to_numpy()
        n = len(close)

        if n == 0:
            for col in ('kalman_level', 'kalman_slope', 'kalman_spread',
                        'kalman_innovation', 'kalman_innov_var',
                        'kalman_z_score', 'kalman_slope_sma', 'kalman_regime'):
                self.df[col] = np.nan
            return self.df

        # Storage arrays
        levels = np.full(n, np.nan)
        slopes = np.full(n, np.nan)
        innovations = np.full(n, np.nan)
        innov_vars = np.full(n, np.nan)

        # Initialise state
        self.x = np.array([close[0], 0.0])
        self.P = np.eye(2)

        levels[0] = close[0]
        slopes[0] = 0.0
        innovations[0] = 0.0
        innov_vars[0] = self.P[0, 0] + self.r_noise

        # Forward pass
        for i in range(1, n):
            x_pred, P_pred = self._predict()
            innov, S = self._update(x_pred, P_pred, close[i])

            levels[i] = self.x[0]
            slopes[i] = self.x[1]
            innovations[i] = innov
            innov_vars[i] = S

        self.df['kalman_level'] = levels
        self.df['kalman_slope'] = slopes
        self.df['kalman_innovation'] = innovations
        self.df['kalman_innov_var'] = innov_vars

        self._compute_derived_columns()

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally compute Kalman outputs for only the last row.

        Falls back to full calculation when state is missing or data is
        too short for rolling windows.

        Args:
            new_df: Updated DataFrame with the new row appended.

        Returns:
            DataFrame with Kalman columns computed for the last row.
        """
        self.df = new_df
        n = len(self.df)

        # Reason: need enough rows for rolling std/quantile and valid prior state
        if self.x is None or n < self.spread_window + 2:
            return self.calculate()

        close = self.df['close'].iloc[-1]
        last_idx = self.df.index[-1]

        # Single predict + update step
        x_pred, P_pred = self._predict()
        innov, S = self._update(x_pred, P_pred, close)

        self.df.loc[last_idx, 'kalman_level'] = self.x[0]
        self.df.loc[last_idx, 'kalman_slope'] = self.x[1]
        self.df.loc[last_idx, 'kalman_innovation'] = innov
        self.df.loc[last_idx, 'kalman_innov_var'] = S

        # Spread
        self.df.loc[last_idx, 'kalman_spread'] = close - self.x[0]

        # Z-score from last spread_window bars
        recent_spread = self.df['kalman_spread'].iloc[-self.spread_window:]
        std = recent_spread.std()
        if std == 0 or pd.isna(std):
            self.df.loc[last_idx, 'kalman_z_score'] = np.nan
        else:
            self.df.loc[last_idx, 'kalman_z_score'] = (close - self.x[0]) / std

        # Slope SMA from last spread_window bars
        self.df.loc[last_idx, 'kalman_slope_sma'] = (
            self.df['kalman_slope'].iloc[-self.spread_window:].mean()
        )

        # Regime from last regime_window bars of innovation variance
        if n >= self.regime_window:
            recent_iv = self.df['kalman_innov_var'].iloc[-self.regime_window:]
            threshold = recent_iv.quantile(self.regime_percentile / 100.0)
            self.df.loc[last_idx, 'kalman_regime'] = int(S > threshold)
        else:
            self.df.loc[last_idx, 'kalman_regime'] = 0

        return self.df
