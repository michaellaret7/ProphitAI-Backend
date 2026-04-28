"""Volatility-of-volatility alpha.

Baltussen, Van Bekkum & Van der Grient (2018, RFS "Unknown Unknowns")
showed that stocks with stable volatility regimes outperform those
with unstable ones — risk that the *level* of risk itself is uncertain
gets compensated. The signal is cross-sectional: stocks whose rolling
volatility is itself volatile underperform the universe median.

    σ_short_t = rolling_std(returns, short_window) at t
    vov_i     = std(σ_short_i over long_window)
    score_i   = median_universe_vov - vov_i

Below-median = stable-vol regime = long candidate (positive score).
Distinct from low-vol — a stock can have low average vol but big
swings in vol from quiet to noisy periods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class VolOfVolAlpha(CrossSectionalAlpha):
    """Cross-sectional vol-of-vol score (median - vov).

    Args:
        short_window: Window for the inner realized-vol estimate
            (default 21).
        long_window: Window over which the std-dev of vols is taken
            (default 252).
        hold_days: Informational ``close_time`` horizon. Vol-of-vol is
            a slow-decay premium.
        min_universe_size: Universe-size floor for the median.
    """

    name = "vol_of_vol"

    def __init__(
        self,
        short_window: int = 21,
        long_window: int = 252,
        hold_days: int = 21,
        min_universe_size: int = 5,
    ):
        if short_window >= long_window:
            raise ValueError(
                f"short_window ({short_window}) must be < long_window "
                f"({long_window})",
            )

        self._short = short_window
        self._long = long_window
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = short_window + long_window

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        vov_by_symbol: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            log_returns = np.log(df["close"]).diff()

            rolling_vol = log_returns.rolling(self._short).std(ddof=1)

            recent = rolling_vol.iloc[-self._long:].dropna()

            if len(recent) < max(2, self._long // 4):
                continue

            vov = float(recent.std(ddof=1))

            if not np.isfinite(vov) or vov <= 0.0:
                continue

            vov_by_symbol[symbol] = vov

        if len(vov_by_symbol) < self._min_universe:
            return None

        median_vov = float(np.median(list(vov_by_symbol.values())))

        return {"vov": vov_by_symbol, "median": median_vov}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        vov_by_symbol: dict[str, float] = stats["vov"]
        median_vov: float = stats["median"]

        vov = vov_by_symbol.get(symbol)

        if vov is None:
            return None

        return median_vov - vov

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized cross-sectional vol-of-vol score across the panel."""
        log_returns = np.log(panel.close).diff()

        rolling_vol = log_returns.rolling(self._short).std(ddof=1)

        vov_panel = rolling_vol.rolling(self._long).std(ddof=1)
        vov_panel = vov_panel.where(vov_panel > 0.0)

        valid_count = vov_panel.count(axis=1)
        median_vov = vov_panel.median(axis=1)

        score = vov_panel.rsub(median_vov, axis=0)

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
