"""Low-volatility alpha (cross-sectional).

The "low-vol anomaly" says low-volatility stocks earn higher risk-adjusted
returns than high-volatility stocks over long horizons. This alpha is
fundamentally *cross-sectional*: its claim is "among THIS universe, the
lower-vol names should be longed and the higher-vol names shorted" — not
"symbol X is going up."

To stay faithful to the Insight contract (direction is a per-symbol
up/flat/down call), the alpha computes the universe-wide median sigma
each bar and emits:

    direction = +1  for below-median-sigma (low vol → long)
    direction = -1  for above-median-sigma (high vol → short)
    magnitude = |sigma - median_sigma|

The PCM can still cross-sectionally z-score magnitude before blending.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alphas.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext


#     ================================
# --> Helper funcs
#     ================================

def _realized_sigma(closes, lookback: int) -> float | None:
    """Realized log-return volatility over the last ``lookback`` bars.

    Returns None if there's insufficient history or the sample produces
    a degenerate sigma (NaN, zero, or negative).
    """
    if len(closes) < lookback + 1:
        return None

    window = closes.iloc[-(lookback + 1):]
    log_returns = np.log(window).diff().dropna()

    if len(log_returns) < 2:
        return None

    sigma = float(log_returns.std())

    if not np.isfinite(sigma) or sigma <= 0.0:
        return None

    return sigma


#     ================================
# --> Alpha
#     ================================

class LowVolAlpha(CrossSectionalAlpha):
    """Cross-sectional low-vol signal.

    Two-phase per bar:
        1. ``compute_universe_stats`` measures realized sigma for every
           ready symbol and returns ``{"sigmas": {...}, "median": float}``
           (or ``None`` if universe is too small this bar).
        2. ``compute_score`` returns ``median - sigma`` for each ticker —
           positive = below-median (long), negative = above (short).

    Args:
        lookback_days: Window over which realized vol is measured.
        hold_days: Informational ``close_time`` horizon. Low-vol is a
            slow-decay premium — longer hold than momentum/breakout.
        min_universe_size: Minimum ready symbols before the alpha emits.
            Too few symbols makes the median meaningless.
    """

    name = "low_vol"

    def __init__(
        self,
        lookback_days: int = 60,
        hold_days: int = 20,
        min_universe_size: int = 3,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = lookback_days + 1

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        sigmas: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            sigma = _realized_sigma(df["close"], self._window)

            if sigma is None:
                continue

            sigmas[symbol] = sigma

        if len(sigmas) < self._min_universe:
            return None

        median_sigma = float(np.median(list(sigmas.values())))

        return {"sigmas": sigmas, "median": median_sigma}

    def compute_score(
        self, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        # Reason: find this ticker's sigma via identity — iterating the
        # dict with an unknown symbol would require passing symbol in.
        # Cleaner: the base already filtered len(df) >= lookback, so we
        # recompute sigma here (cheap vs. plumbing a symbol key in).
        sigma = _realized_sigma(df["close"], self._window)

        if sigma is None:
            return None

        median_sigma: float = stats["median"]

        # Positive => below-median-sigma (low vol → long).
        return median_sigma - sigma
