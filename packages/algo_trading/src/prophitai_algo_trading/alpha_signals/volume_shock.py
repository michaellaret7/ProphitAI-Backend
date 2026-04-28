"""Volume-shock alpha — high-volume directional moves persist.

Today's volume z-score multiplied by the recent return. High-volume
green prints (up move on heavy turnover) signal institutional buying
that tends to extend over the next few sessions. High-volume red
prints signal liquidation flow that also persists short-term.

    vol_z      = (volume - rolling_mean) / rolling_std
    ret_short  = close[t] / close[t - W] - 1
    score      = vol_z * ret_short

Distinct from ``TrendVolumeAlpha`` (which gates an MACD histogram by
volume z, focusing on smoothed trend regime). This alpha amplifies the
*raw recent return* by volume, capturing news-driven flow rather than
established trend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Helper funcs
#     ================================

def _volume_zscore_now(volume, lookback: int) -> float:
    """Z-score of today's volume vs rolling mean/std over ``lookback`` bars."""
    recent = volume.iloc[-lookback:]

    if len(recent) < 2:
        return 0.0

    mean_v = float(recent.mean())
    std_v = float(recent.std())

    if std_v <= 0.0:
        return 0.0

    return (float(volume.iloc[-1]) - mean_v) / std_v


#     ================================
# --> Alpha
#     ================================

class VolumeShockAlpha(PerSymbolAlpha):
    """Volume z-score scaled by recent close-to-close return.

    Args:
        return_window: Bars over which the recent return is measured
            (default 3 — captures multi-day flow without smoothing it
            out).
        volume_lookback: Rolling window for the volume z-score
            (default 20).
        hold_days: Informational ``close_time`` horizon — flow-driven
            persistence is short-lived.
    """

    name = "volume_shock"
    required_columns = ("close", "volume")

    def __init__(
        self,
        return_window: int = 3,
        volume_lookback: int = 20,
        hold_days: int = 3,
    ):
        self._return_window = return_window
        self._vol_lookback = volume_lookback
        self.hold_days = hold_days

        # Reason: need the larger of the two windows + 1 for the return base.
        self.lookback = max(return_window, volume_lookback) + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        start_price = float(closes.iloc[-(self._return_window + 1)])
        current = float(closes.iloc[-1])

        if start_price <= 0.0 or current <= 0.0:
            return None

        recent_return = current / start_price - 1.0

        vol_z = _volume_zscore_now(df["volume"], self._vol_lookback)

        return vol_z * recent_return

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized volume-shock score across the full panel.

        Per-ticker rolling volume z-score multiplied by the W-bar return.
        """
        if panel.volume is None:
            raise ValueError(
                "VolumeShockAlpha.compute_panel requires panel.volume",
            )

        volume = panel.volume

        vol_mean = volume.rolling(self._vol_lookback).mean()
        vol_std = volume.rolling(self._vol_lookback).std()

        vol_z = (volume - vol_mean) / vol_std.where(vol_std > 0.0)
        vol_z = vol_z.fillna(0.0)

        ret = panel.close.pct_change(self._return_window).fillna(0.0)

        return vol_z * ret
