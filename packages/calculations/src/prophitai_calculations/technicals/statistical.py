"""Statistical indicators — z-score, autocorrelation, Hurst, OU half-life.

All returned Series have NaN rows dropped.
"""

from typing import cast

import numpy as np
import pandas as pd


# ================================
# --> Helper funcs
# ================================

def _rescaled_range(series: np.ndarray) -> float | None:
    """Rescaled range R/S for a single contiguous series.

    R = max(cumulative deviations) - min(cumulative deviations).
    S = sample standard deviation.
    """
    if len(series) < 2:
        return None

    mean_adjusted = series - series.mean()
    cumulative = np.cumsum(mean_adjusted)
    r = cumulative.max() - cumulative.min()
    s = series.std(ddof=1)

    if s == 0 or r == 0:
        return None

    return float(r / s)


def _expected_rs_anis_lloyd(n: int) -> float:
    """Expected R/S under the H=0.5 null (Anis-Lloyd 1976 / Peters 1994).

    Used to correct the finite-sample upward bias of the classical R/S
    estimator. For small n, raw R/S on i.i.d. data gives H > 0.5; dividing
    by this expected value before fitting centers the estimator.
    """
    if n < 2:
        return 1.0

    # sum_{i=1}^{n-1} sqrt((n-i)/i)
    i = np.arange(1, n)
    partial_sum = float(np.sum(np.sqrt((n - i) / i)))

    if n <= 340:
        # Exact form with Gamma ratio — accurate for small n
        from math import lgamma, pi, sqrt
        ln_ratio = lgamma((n - 1) / 2) - lgamma(n / 2)
        factor = np.exp(ln_ratio) / sqrt(pi)
    else:
        # Asymptotic approximation for large n
        factor = 1.0 / np.sqrt(n * np.pi / 2)

    return ((n - 0.5) / n) * factor * partial_sum


def calc_z_score(close: pd.Series, window: int = 50) -> pd.Series:
    """Calculate rolling Z-score of price.

    Z = (price - rolling_mean) / rolling_std.
    |Z| > 2 = statistically extreme. Used for mean-reversion detection.
    Common windows: 20, 50, 90 days.
    """
    rolling_mean = close.rolling(window=window, min_periods=window).mean()
    rolling_std = close.rolling(window=window, min_periods=window).std()
    z = cast(pd.Series, (close - rolling_mean) / rolling_std.replace(0, np.nan))

    return z.dropna()


def calc_autocorrelation(
    close: pd.Series,
    lags: list[int] | None = None,
    window: int = 252,
) -> dict[int, pd.Series]:
    """Calculate rolling autocorrelation of returns at specified lags.

    Positive autocorrelation = trending behavior (momentum).
    Negative autocorrelation = mean-reverting behavior.
    Near zero = random walk (no exploitable pattern).

    Args:
        close: Adjusted close price series.
        lags: List of lag periods to compute. Defaults to [1, 5, 10, 21].
        window: Rolling window for autocorrelation estimation.

    Returns:
        Dict mapping lag → autocorrelation Series.
    """
    if lags is None:
        lags = [1, 5, 10, 21]

    daily_returns = close.pct_change(fill_method=None).dropna()
    result: dict[int, pd.Series] = {}

    for lag in lags:
        autocorr = cast(
            pd.Series,
            daily_returns.rolling(window=window, min_periods=window).apply(
                lambda x: x.autocorr(lag=lag), raw=False,  # noqa: B023
            ),
        )
        result[lag] = autocorr.dropna()

    return result


def calc_hurst_exponent(close: pd.Series, window: int = 252) -> float | None:
    """Calculate Hurst exponent via rescaled-range (R/S) analysis on log-returns.

    H < 0.5 = mean-reverting (anti-persistent).
    H = 0.5 = random walk (no structure).
    H > 0.5 = trending (persistent).

    Applied to log-returns (stationary) rather than raw prices. Uses a
    log-log regression of R/S across multiple chunk sizes.

    Args:
        close: Adjusted close price series.
        window: Trailing window of observations. Default 252.

    Returns:
        Hurst exponent in [0, 1], or None if the regression is degenerate
        (insufficient data, zero variance, all zero returns).
    """
    # Reason: guard against zero/negative prices before log to avoid -inf/NaN
    prev = close.shift(1)
    ratio = close / prev
    ratio = ratio.where(ratio > 0)
    log_returns = np.log(ratio).dropna()

    if len(log_returns) < window:
        return None

    series = log_returns.iloc[-window:].to_numpy(dtype=float)

    # Reason: pick chunk sizes spanning small to large to get a robust regression slope
    chunk_sizes = [8, 16, 32, 64, 128]
    chunk_sizes = [n for n in chunk_sizes if n <= len(series) // 2]

    if len(chunk_sizes) < 2:
        return None

    log_n: list[float] = []
    log_rs_normalized: list[float] = []

    for n in chunk_sizes:
        num_chunks = len(series) // n
        rs_values: list[float] = []

        for i in range(num_chunks):
            chunk = series[i * n : (i + 1) * n]
            rs = _rescaled_range(chunk)
            if rs is not None:
                rs_values.append(rs)

        if rs_values:
            # Reason: normalize by Anis-Lloyd expected R/S to remove small-sample bias
            expected = _expected_rs_anis_lloyd(n)
            log_n.append(np.log(n))
            log_rs_normalized.append(np.log(np.mean(rs_values) / expected))

    if len(log_n) < 2:
        return None

    # Reason: after normalization, slope estimates (H - 0.5); add 0.5 to get H
    slope, _ = np.polyfit(log_n, log_rs_normalized, 1)

    if np.isnan(slope):
        return None

    return float(slope + 0.5)


def calc_ou_half_life(series: pd.Series, window: int = 252) -> float | None:
    """Calculate Ornstein-Uhlenbeck mean-reversion half-life.

    Run OLS: delta_x_t = alpha + beta * x_{t-1} + epsilon.
    Half-life = -ln(2) / beta (only valid when beta < 0).

    Input MUST be a stationary series — log-returns, price-minus-rolling-mean,
    or a cointegration residual. Applied to raw prices, the regression is
    meaningless because prices are non-stationary I(1).

    Args:
        series: Stationary time series (e.g. log-returns).
        window: Trailing window of observations. Default 252.

    Returns:
        Half-life in periods (trading days for daily data). None when:
          - beta >= 0 (no mean reversion)
          - regression is degenerate
          - half-life > window (practically not mean-reverting)
    """
    clean = series.dropna()

    if len(clean) < window:
        return None

    x = clean.iloc[-window:].to_numpy(dtype=float)

    # Reason: lstsq calls LAPACK which prints to stderr (bypassing Python warnings)
    # when inputs contain Inf or are rank-deficient. Filter + validate up front.
    if not np.all(np.isfinite(x)):
        return None

    lagged = x[:-1]
    delta = x[1:] - lagged

    # Degenerate lagged series (constant) → design matrix is rank-deficient
    if np.ptp(lagged) == 0:
        return None

    design = np.column_stack([np.ones(len(lagged)), lagged])

    if not (np.all(np.isfinite(design)) and np.all(np.isfinite(delta))):
        return None

    try:
        coeffs, *_ = np.linalg.lstsq(design, delta, rcond=None)
    except (np.linalg.LinAlgError, ValueError):
        return None

    beta = float(coeffs[1])

    if beta >= 0 or np.isnan(beta):
        return None

    half_life = -np.log(2) / beta

    if np.isnan(half_life) or np.isinf(half_life) or half_life > window:
        return None

    return float(half_life)
