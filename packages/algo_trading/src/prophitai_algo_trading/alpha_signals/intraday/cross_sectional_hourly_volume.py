"""Cross-sectional hourly volume continuation alpha.

For each bar, score every ticker by the row-z-score of dollar volume,
signed by the bar's return. High-dollar-volume up-bars are persistent
institutional buying; high-dollar-volume down-bars are persistent
selling. Cross-sectional normalization makes mega-caps comparable to
mid-caps.

    dollar_vol = close * volume
    z_dv       = row z-score of dollar_vol across universe
    ret        = (close[t] / close[t-1]) - 1
    score      = z_dv * sign(ret)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class CrossSectionalHourlyVolumeAlpha(CrossSectionalAlpha):
    """Row z-score of dollar volume, signed by 1-bar return."""

    name = "xs_hourly_volume"
    required_columns = ("close", "volume")

    def __init__(
        self,
        hold_days: int = 1,
        min_universe_size: int = 5,
    ):
        self.hold_days = hold_days
        self._min_universe = min_universe_size
        self.lookback = 2

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        dv: dict[str, float] = {}
        ret: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"]
            volumes = df["volume"]

            cur_close = float(closes.iloc[-1])
            cur_vol = float(volumes.iloc[-1])
            prev_close = float(closes.iloc[-2])

            if cur_close <= 0.0 or prev_close <= 0.0 or cur_vol <= 0.0:
                continue

            dv[symbol] = cur_close * cur_vol
            ret[symbol] = cur_close / prev_close - 1.0

        if len(dv) < self._min_universe:
            return None

        values = list(dv.values())
        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1))

        if std <= 0.0:
            return None

        return {"dv": dv, "ret": ret, "mean": mean, "std": std}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        dv = stats["dv"].get(symbol)
        ret = stats["ret"].get(symbol)

        if dv is None or ret is None:
            return None

        z = (dv - stats["mean"]) / stats["std"]

        return z * np.sign(ret)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        if panel.volume is None:
            raise ValueError(
                "CrossSectionalHourlyVolumeAlpha.compute_panel requires panel.volume",
            )

        dollar_vol = panel.close * panel.volume

        row_mean = dollar_vol.mean(axis=1)
        row_std = dollar_vol.std(axis=1, ddof=1)

        z = dollar_vol.sub(row_mean, axis=0).div(
            row_std.where(row_std > 0.0), axis=0,
        )

        ret = panel.close.pct_change(1)
        sign = np.sign(ret).fillna(0.0)

        valid_count = z.count(axis=1)

        score = z * sign

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
