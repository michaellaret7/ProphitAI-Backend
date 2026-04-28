"""Hourly OBV slope alpha.

Granville OBV computed on hourly bars: cumulative sign(Δclose) × volume.
The N-bar slope captures whether volume is consistently flowing in the
same direction as price action over recent hours — institutional
accumulation/distribution at intraday horizon.

    obv_t = obv_{t-1} + sign(close_t - close_{t-1}) * volume_t
    score = N-bar linear slope of obv, normalized by mean volume
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class HourlyOBVAlpha(PerSymbolAlpha):
    """N-bar slope of cumulative signed-volume on hourly bars."""

    name = "hourly_obv"
    required_columns = ("close", "volume")

    def __init__(
        self,
        slope_window: int = 8,
        history_bars: int = 40,
        hold_days: int = 1,
    ):
        self._slope_window = slope_window
        self._history = history_bars
        self.hold_days = hold_days

        self.lookback = history_bars + 1

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
        if panel.volume is None:
            raise ValueError(
                "HourlyOBVAlpha.compute_panel requires panel.volume",
            )

        closes = panel.close
        volume = panel.volume

        signed_vol = np.sign(closes.diff().fillna(0.0)) * volume
        obv = signed_vol.cumsum()

        n = self._slope_window
        x = np.arange(n, dtype=float)
        x_mean = x.mean()
        x_dev = x - x_mean
        x_var = float((x_dev ** 2).sum())

        def _slope(values: np.ndarray) -> float:
            return float((x_dev * (values - values.mean())).sum() / x_var)

        slope = obv.rolling(n).apply(_slope, raw=True)

        mean_vol = volume.rolling(n).mean()

        return slope / mean_vol.where(mean_vol > 0.0)
