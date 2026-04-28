"""On-Balance Volume slope alpha.

Granville (1963) On-Balance Volume cumulates signed volume — adding the
day's volume to a running total when the close is up, subtracting it
when down. The *slope* of OBV over a recent window measures whether
volume is consistently flowing in the same direction as price action.

    obv_t = obv_{t-1} + sign(close_t - close_{t-1}) * volume_t
    score = N-day linear-regression slope of obv, normalized by
            mean volume so cross-sectional comparisons are scale-free

Distinct from a contemporaneous volume × return signal: OBV is a
*path-dependent accumulation* — a stock with persistent low-volume
buying days will show a positive OBV slope even if no individual day
prints a volume-spike.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class OBVSlopeAlpha(PerSymbolAlpha):
    """N-day slope of cumulative signed-volume, scale-normalized.

    Args:
        slope_window: Window for the OBV regression slope (default 20).
        history_days: Bars used to compute OBV before slicing the window.
        hold_days: Informational ``close_time`` horizon. OBV regimes
            persist over weeks.
    """

    name = "obv_slope"
    required_columns = ("close", "volume")

    def __init__(
        self,
        slope_window: int = 20,
        history_days: int = 60,
        hold_days: int = 10,
    ):
        self._slope_window = slope_window
        self._history = history_days
        self.hold_days = hold_days

        self.lookback = history_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"].iloc[-(self._history + 1):]
        volumes = df["volume"].iloc[-(self._history + 1):]

        signed_vol = np.sign(closes.diff().fillna(0.0)) * volumes
        obv = signed_vol.cumsum()

        recent = obv.iloc[-self._slope_window:].to_numpy(dtype=float)

        if len(recent) < self._slope_window:
            return None

        x = np.arange(len(recent), dtype=float)

        slope = float(np.polyfit(x, recent, 1)[0])

        mean_vol = float(volumes.iloc[-self._slope_window:].mean())

        if mean_vol <= 0.0:
            return None

        return slope / mean_vol

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized OBV slope across the full ``[date x ticker]`` panel.

        Cumulative signed volume per ticker, then a rolling regression
        slope (closed-form) divided by rolling mean volume.
        """
        if panel.volume is None:
            raise ValueError(
                "OBVSlopeAlpha.compute_panel requires panel.volume",
            )

        closes = panel.close
        volume = panel.volume

        signed_vol = np.sign(closes.diff().fillna(0.0)) * volume
        obv = signed_vol.cumsum()

        n = self._slope_window
        x = np.arange(n, dtype=float)
        x_mean = x.mean()
        x_var = ((x - x_mean) ** 2).sum()

        # Reason: rolling slope via closed-form OLS — sum((x-xmean)*(y-ymean))/sum((x-xmean)^2).
        # Implemented as rolling sum of x*y minus n * xmean * ymean.
        x_dev = (x - x_mean).reshape(-1, 1)

        def _slope(window_values: np.ndarray) -> float:
            return float((x_dev.flatten() * (window_values - window_values.mean())).sum() / x_var)

        slope = obv.rolling(n).apply(_slope, raw=True)

        mean_vol = volume.rolling(n).mean()

        return slope / mean_vol.where(mean_vol > 0.0)
