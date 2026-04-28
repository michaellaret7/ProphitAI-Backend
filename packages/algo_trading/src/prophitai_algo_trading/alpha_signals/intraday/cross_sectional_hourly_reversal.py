"""Cross-sectional hourly reversal alpha.

For each hourly bar, compute every ticker's 5-bar return, z-score
across the universe, and negate. Names that have outperformed the
cross-section short-term tend to mean-revert; names that have
underperformed tend to bounce.

    ret_i_t = (close_i[t] / close_i[t-W]) - 1
    z_i_t   = (ret_i - mean(ret)) / std(ret)         row-wise
    score_i = -z_i_t

Distinct from per-symbol reversal (``OneBarReversalAlpha``): this is
*relative* to the universe at each timestamp.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class CrossSectionalHourlyReversalAlpha(CrossSectionalAlpha):
    """Negated row z-score of N-bar return."""

    name = "xs_hourly_reversal"

    def __init__(
        self,
        return_window: int = 5,
        hold_days: int = 1,
        min_universe_size: int = 5,
    ):
        self._window = return_window
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = return_window + 1

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        returns: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"]

            start_price = float(closes.iloc[-(self._window + 1)])
            current = float(closes.iloc[-1])

            if start_price <= 0.0 or current <= 0.0:
                continue

            returns[symbol] = current / start_price - 1.0

        if len(returns) < self._min_universe:
            return None

        values = list(returns.values())
        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1))

        if std <= 0.0:
            return None

        return {"returns": returns, "mean": mean, "std": std}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        returns: dict[str, float] = stats["returns"]
        mean: float = stats["mean"]
        std: float = stats["std"]

        ret = returns.get(symbol)

        if ret is None:
            return None

        return -((ret - mean) / std)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        ret = panel.close.pct_change(self._window)

        valid_count = ret.count(axis=1)

        row_mean = ret.mean(axis=1)
        row_std = ret.std(axis=1, ddof=1)

        z = ret.sub(row_mean, axis=0).div(row_std.where(row_std > 0.0), axis=0)

        thin_rows = valid_count < self._min_universe
        z.loc[thin_rows, :] = 0.0

        return (-z).fillna(0.0)
