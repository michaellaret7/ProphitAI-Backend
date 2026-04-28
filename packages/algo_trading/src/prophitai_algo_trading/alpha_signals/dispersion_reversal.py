"""Cross-sectional dispersion reversal alpha.

Each bar, score every ticker by how far its recent return sits from the
universe mean (in z-score units), then negate. Extreme outperformers
fade; extreme underperformers bounce. The "dispersion" anomaly: cross-
sectional return spread mean-reverts at short horizons.

    ret_i      = close_i[t] / close_i[t - W] - 1
    z_i        = (ret_i - mean(ret)) / std(ret)
    score_i    = -z_i

Positive z (winner) => negative score (short candidate).
Negative z (loser) => positive score (long candidate).

Distinct from the per-symbol ``ShortTermReversalAlpha`` because the
signal is normalized against the *universe* — a stock up 3% in a week
where everyone is up 5% is a *relative* loser even though its raw
return is positive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class DispersionReversalAlpha(CrossSectionalAlpha):
    """Cross-sectional return z-score, negated.

    Two-phase per bar:
        1. ``compute_universe_stats`` collects each ticker's W-bar return
           and computes universe mean + std.
        2. ``compute_score`` returns ``-z_score(ticker_return)``.

    Args:
        lookback_days: Return window in trading days (default 5 = one
            trading week — same horizon as ``ShortTermReversalAlpha``,
            but normalized cross-sectionally).
        hold_days: Informational ``close_time`` horizon.
        min_universe_size: Minimum ready symbols before emitting (the
            z-score is meaningless on a thin universe).
    """

    name = "dispersion_reversal"

    def __init__(
        self,
        lookback_days: int = 5,
        hold_days: int = 3,
        min_universe_size: int = 5,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = lookback_days + 1

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

        # Reason: negate — relative outperformer is the short candidate.
        return -(ret - mean) / std

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized dispersion-reversal across the full panel.

        Per-bar: compute the W-bar return for every ticker, then row-wise
        z-score across the universe. Negate so winners → short, losers →
        long. Rows where the universe is too thin emit zeros.
        """
        ret = panel.close.pct_change(self._window)

        valid_count = ret.count(axis=1)

        row_mean = ret.mean(axis=1)
        row_std = ret.std(axis=1, ddof=1)

        z = ret.sub(row_mean, axis=0).div(row_std.where(row_std > 0.0), axis=0)

        thin_rows = valid_count < self._min_universe
        z.loc[thin_rows, :] = 0.0

        return (-z).fillna(0.0)
