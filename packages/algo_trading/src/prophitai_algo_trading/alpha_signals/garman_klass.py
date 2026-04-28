"""Garman-Klass volatility — cross-sectional low-vol via OHLC estimator.

Garman & Klass (1980) showed that an estimator using all four OHLC
prints is ~7-8x more efficient than close-to-close volatility for
estimating realized volatility. Using it cross-sectionally captures
the low-vol anomaly through a different statistical lens than plain
close-to-close, often picking different names.

    σ²_GK = 0.5 * (ln(H/L))² - (2 ln 2 - 1) * (ln(C/O))²

Per ticker the score is ``median_universe_GK - ticker_GK`` (positive =
below-median = long candidate). Distinct from ``LowVolAlpha`` because
that uses only close-to-close log-return std-dev — Garman-Klass adds
intra-bar high/low information that captures price churn missed by
endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


_CONST = 2.0 * np.log(2.0) - 1.0


#     ================================
# --> Helper funcs
#     ================================

def _garman_klass_window(df: "pd.DataFrame", window: int) -> float | None:
    """Mean Garman-Klass variance over the trailing ``window`` bars."""
    recent = df.iloc[-window:]

    high = recent["high"]
    low = recent["low"]
    close = recent["close"]
    open_ = recent["open"]

    if (high <= 0.0).any() or (low <= 0.0).any():
        return None

    if (close <= 0.0).any() or (open_ <= 0.0).any():
        return None

    log_hl = np.log(high / low)
    log_co = np.log(close / open_)

    gk_var = 0.5 * (log_hl ** 2) - _CONST * (log_co ** 2)

    mean_var = float(gk_var.mean())

    if not np.isfinite(mean_var) or mean_var <= 0.0:
        return None

    return mean_var


#     ================================
# --> Alpha
#     ================================

class GarmanKlassVolAlpha(CrossSectionalAlpha):
    """Cross-sectional Garman-Klass low-vol score.

    Args:
        lookback_days: Window for averaging the GK variance.
        hold_days: Informational ``close_time`` horizon. Vol-style
            premia decay slowly — hold longer than mean-reversion.
        min_universe_size: Universe-size floor below which the median
            is meaningless and the alpha emits nothing.
    """

    name = "garman_klass"
    required_columns = ("open", "high", "low", "close")

    def __init__(
        self,
        lookback_days: int = 60,
        hold_days: int = 20,
        min_universe_size: int = 5,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = lookback_days

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        gk_by_symbol: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            value = _garman_klass_window(df, self._window)

            if value is None:
                continue

            gk_by_symbol[symbol] = value

        if len(gk_by_symbol) < self._min_universe:
            return None

        median_gk = float(np.median(list(gk_by_symbol.values())))

        return {"gk": gk_by_symbol, "median": median_gk}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        gk_by_symbol: dict[str, float] = stats["gk"]
        median_gk: float = stats["median"]

        gk = gk_by_symbol.get(symbol)

        if gk is None:
            return None

        return median_gk - gk

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized cross-sectional GK across the full panel.

        Per (date, ticker) GK variance, then a row-wise spread vs. the
        universe median. Rows with too few valid sigmas emit zeros.
        """
        if panel.high is None or panel.low is None or panel.open is None:
            raise ValueError(
                "GarmanKlassVolAlpha.compute_panel requires panel.open, "
                "panel.high, panel.low",
            )

        high = panel.high
        low = panel.low
        close = panel.close
        open_ = panel.open

        log_hl = np.log(high / low.where(low > 0.0))
        log_co = np.log(close / open_.where(open_ > 0.0))

        gk_per_bar = 0.5 * (log_hl ** 2) - _CONST * (log_co ** 2)

        gk_panel = gk_per_bar.rolling(self._window).mean()

        # Reason: degenerate variance (NaN, non-positive) cleared so it
        # doesn't pollute the row median.
        gk_panel = gk_panel.where(gk_panel > 0.0)

        valid_count = gk_panel.count(axis=1)
        median_gk = gk_panel.median(axis=1)

        score = gk_panel.rsub(median_gk, axis=0)

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
