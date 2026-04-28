"""Volume-spike continuation alpha (intraday flow).

A bar with extreme volume on hourly data signals fresh institutional
flow that frequently extends into subsequent bars. The signal:

    vol_z   = (volume - rolling_mean) / rolling_std    over past 20 bars
    ret     = (close[t] - close[t-1]) / close[t-1]
    score   = vol_z * sign(ret)

Floored at zero on the volume side so quiet bars contribute nothing —
this alpha *only* fires when volume is genuinely above average.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class VolumeSpikeContinuationAlpha(PerSymbolAlpha):
    """Volume z-score × sign(return), floored at 0 on the volume side."""

    name = "volume_spike_continuation"
    required_columns = ("close", "volume")

    def __init__(
        self,
        volume_window: int = 20,
        return_window: int = 1,
        hold_days: int = 1,
    ):
        self._vol_window = volume_window
        self._ret_window = return_window
        self.hold_days = hold_days

        self.lookback = max(volume_window, return_window) + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent_vol = df["volume"].iloc[-self._vol_window:]

        if len(recent_vol) < 2:
            return None

        mean_v = float(recent_vol.mean())
        std_v = float(recent_vol.std(ddof=1))

        if std_v <= 0.0:
            return 0.0

        cur_vol = float(df["volume"].iloc[-1])
        vol_z = (cur_vol - mean_v) / std_v

        if vol_z <= 0.0:
            return 0.0

        closes = df["close"]
        prev_close = float(closes.iloc[-(self._ret_window + 1)])
        cur_close = float(closes.iloc[-1])

        if prev_close <= 0.0 or cur_close <= 0.0:
            return None

        ret = (cur_close / prev_close) - 1.0

        return vol_z * np.sign(ret)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        if panel.volume is None:
            raise ValueError(
                "VolumeSpikeContinuationAlpha.compute_panel requires panel.volume",
            )

        volume = panel.volume

        vol_mean = volume.rolling(self._vol_window).mean()
        vol_std = volume.rolling(self._vol_window).std(ddof=1)

        vol_z = (volume - vol_mean) / vol_std.where(vol_std > 0.0)
        vol_z = vol_z.clip(lower=0.0).fillna(0.0)

        ret = panel.close.pct_change(self._ret_window)

        return vol_z * np.sign(ret).fillna(0.0)
