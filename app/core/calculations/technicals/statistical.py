"""Statistical indicators — z-score, autocorrelation, and regime signals.

All returned Series have NaN rows dropped.
"""

from typing import cast

import numpy as np
import pandas as pd


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
