"""VWAP + Hurst Exponent indicator for 1-minute crypto HFT.

Computes rolling VWAP as a dynamic fair-value anchor and the Hurst exponent
via Rescaled Range (R/S) analysis for regime classification. Designed for
1-minute BTC data but works on any OHLCV timeframe.

Outputs:
    vwap            - Rolling volume-weighted average price.
    vwap_z_score    - Z-score of price deviation from VWAP (normalised by ATR).
    atr             - Average True Range for dynamic thresholds.
    hurst           - Rolling Hurst exponent (0-1).
    hurst_regime    - 0 = mean-reverting, 1 = trending, 2 = random walk.
    ema_fast        - Fast EMA for momentum signals in trending regime.
    ema_slow        - Slow EMA for momentum signals in trending regime.

Supports both full batch calculation and efficient incremental updates.
"""

import numpy as np
import pandas as pd

from prophitai_algo_trading.utils.normalize_columns import normalize_columns


# ================================
# --> Helper funcs
# ================================

def _compute_hurst_rs(series: np.ndarray) -> float:
    """Compute Hurst exponent using Rescaled Range (R/S) analysis.

    Uses multiple sub-series lengths and fits log-log regression to estimate H.
    Returns NaN if the series is too short or constant.
    """
    n = len(series)
    if n < 20:
        return np.nan

    # Reason: use power-of-2 subdivision lengths for clean R/S estimation
    max_k = int(np.log2(n))
    if max_k < 2:
        return np.nan

    sizes = [int(2 ** i) for i in range(2, max_k + 1) if 2 ** i <= n // 2]
    if len(sizes) < 2:
        return np.nan

    rs_values = []
    for size in sizes:
        num_chunks = n // size
        rs_chunk = []
        for j in range(num_chunks):
            chunk = series[j * size:(j + 1) * size]
            mean_chunk = np.mean(chunk)
            deviations = chunk - mean_chunk
            cumulative = np.cumsum(deviations)
            r = np.max(cumulative) - np.min(cumulative)
            s = np.std(chunk, ddof=1)
            if s > 0:
                rs_chunk.append(r / s)
        if rs_chunk:
            rs_values.append((np.log(size), np.log(np.mean(rs_chunk))))

    if len(rs_values) < 2:
        return np.nan

    log_sizes, log_rs = zip(*rs_values)
    log_sizes = np.array(log_sizes)
    log_rs = np.array(log_rs)

    # Reason: simple linear regression slope = Hurst exponent
    slope, _ = np.polyfit(log_sizes, log_rs, 1)
    return np.clip(slope, 0.0, 1.0)


def _rolling_hurst(close: np.ndarray, window: int) -> np.ndarray:
    """Compute rolling Hurst exponent over a numpy array."""
    n = len(close)
    hurst = np.full(n, np.nan)
    returns = np.diff(close) / close[:-1]

    for i in range(window, n):
        ret_window = returns[i - window:i]
        if np.all(np.isfinite(ret_window)):
            hurst[i] = _compute_hurst_rs(ret_window)

    return hurst


class VwapHurst:
    """Rolling VWAP + Hurst Exponent indicator with regime detection.

    Args:
        df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.
        vwap_window: Rolling window for VWAP calculation (bars).
        hurst_window: Lookback for Hurst exponent estimation.
        atr_period: ATR lookback period.
        ema_fast_period: Fast EMA period for momentum signals.
        ema_slow_period: Slow EMA period for momentum signals.
        hurst_mr_threshold: Hurst below this = mean-reverting regime.
        hurst_trend_threshold: Hurst above this = trending regime.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        vwap_window: int = 60,
        hurst_window: int = 120,
        atr_period: int = 14,
        ema_fast_period: int = 8,
        ema_slow_period: int = 21,
        hurst_mr_threshold: float = 0.45,
        hurst_trend_threshold: float = 0.55,
    ):
        self.df = normalize_columns(df.copy())
        self.vwap_window = vwap_window
        self.hurst_window = hurst_window
        self.atr_period = atr_period
        self.ema_fast_period = ema_fast_period
        self.ema_slow_period = ema_slow_period
        self.hurst_mr_threshold = hurst_mr_threshold
        self.hurst_trend_threshold = hurst_trend_threshold

        self.calculate()

    def _compute_atr(self) -> None:
        """Compute Average True Range."""
        high = self.df['high']
        low = self.df['low']
        prev_close = self.df['close'].shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        self.df['atr'] = tr.ewm(span=self.atr_period, adjust=False).mean()

    def _compute_vwap(self) -> None:
        """Compute rolling VWAP over the session window."""
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        tp_vol = typical_price * self.df['volume']

        rolling_tp_vol = tp_vol.rolling(self.vwap_window, min_periods=1).sum()
        rolling_vol = self.df['volume'].rolling(self.vwap_window, min_periods=1).sum()

        # Reason: avoid division by zero when volume is 0 in a window
        rolling_vol = rolling_vol.replace(0, np.nan)
        self.df['vwap'] = rolling_tp_vol / rolling_vol

    def _compute_vwap_z_score(self) -> None:
        """Compute z-score of price deviation from VWAP, normalised by ATR."""
        deviation = self.df['close'] - self.df['vwap']
        atr = self.df['atr']
        # Reason: normalise by ATR so threshold works across different price/vol regimes
        atr_safe = atr.replace(0, np.nan)
        self.df['vwap_z_score'] = deviation / atr_safe

    def _compute_hurst(self) -> None:
        """Compute rolling Hurst exponent and classify regime."""
        close = self.df['close'].to_numpy()
        self.df['hurst'] = _rolling_hurst(close, self.hurst_window)

        # Regime classification: 0 = mean-reverting, 1 = trending, 2 = random walk
        hurst = self.df['hurst']
        self.df['hurst_regime'] = np.where(
            hurst < self.hurst_mr_threshold, 0,
            np.where(hurst > self.hurst_trend_threshold, 1, 2)
        )
        # Reason: default NaN regime to random walk (safest — stay flat)
        self.df['hurst_regime'] = self.df['hurst_regime'].fillna(2).astype(int)

    def _compute_emas(self) -> None:
        """Compute fast and slow EMAs for momentum signals."""
        self.df['ema_fast'] = self.df['close'].ewm(
            span=self.ema_fast_period, adjust=False
        ).mean()
        self.df['ema_slow'] = self.df['close'].ewm(
            span=self.ema_slow_period, adjust=False
        ).mean()

    def calculate(self) -> pd.DataFrame:
        """Full batch calculation of all indicator columns."""
        if self.df.empty:
            for col in ('vwap', 'vwap_z_score', 'atr', 'hurst',
                        'hurst_regime', 'ema_fast', 'ema_slow'):
                self.df[col] = np.nan
            return self.df

        self._compute_atr()
        self._compute_vwap()
        self._compute_vwap_z_score()
        self._compute_hurst()
        self._compute_emas()

        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicators for the last row only.

        Falls back to full calculation when insufficient data for rolling windows.
        """
        self.df = new_df
        n = len(self.df)

        if n < self.hurst_window + 2:
            return self.calculate()

        last_idx = self.df.index[-1]
        close = self.df['close'].iloc[-1]
        high = self.df['high'].iloc[-1]
        low = self.df['low'].iloc[-1]
        prev_close = self.df['close'].iloc[-2]

        # ATR incremental: EWM update
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        prev_atr = self.df['atr'].iloc[-2]
        if pd.isna(prev_atr):
            return self.calculate()
        alpha = 2.0 / (self.atr_period + 1)
        self.df.loc[last_idx, 'atr'] = alpha * tr + (1 - alpha) * prev_atr

        # VWAP incremental: rolling sum
        window_slice = self.df.iloc[-self.vwap_window:]
        tp = (window_slice['high'] + window_slice['low'] + window_slice['close']) / 3
        tp_vol_sum = (tp * window_slice['volume']).sum()
        vol_sum = window_slice['volume'].sum()
        self.df.loc[last_idx, 'vwap'] = tp_vol_sum / vol_sum if vol_sum > 0 else np.nan

        # VWAP z-score
        deviation = close - self.df.loc[last_idx, 'vwap']
        atr_val = self.df.loc[last_idx, 'atr']
        self.df.loc[last_idx, 'vwap_z_score'] = (
            deviation / atr_val if atr_val > 0 else np.nan
        )

        # Hurst: recompute for last window
        close_arr = self.df['close'].iloc[-self.hurst_window - 1:].to_numpy()
        returns = np.diff(close_arr) / close_arr[:-1]
        if np.all(np.isfinite(returns)):
            h = _compute_hurst_rs(returns)
        else:
            h = np.nan
        self.df.loc[last_idx, 'hurst'] = h

        # Regime
        if np.isnan(h):
            self.df.loc[last_idx, 'hurst_regime'] = 2
        elif h < self.hurst_mr_threshold:
            self.df.loc[last_idx, 'hurst_regime'] = 0
        elif h > self.hurst_trend_threshold:
            self.df.loc[last_idx, 'hurst_regime'] = 1
        else:
            self.df.loc[last_idx, 'hurst_regime'] = 2

        # EMA incremental: EWM recursive formula
        fast_alpha = 2.0 / (self.ema_fast_period + 1)
        slow_alpha = 2.0 / (self.ema_slow_period + 1)
        prev_ema_fast = self.df['ema_fast'].iloc[-2]
        prev_ema_slow = self.df['ema_slow'].iloc[-2]
        self.df.loc[last_idx, 'ema_fast'] = fast_alpha * close + (1 - fast_alpha) * prev_ema_fast
        self.df.loc[last_idx, 'ema_slow'] = slow_alpha * close + (1 - slow_alpha) * prev_ema_slow

        return self.df
