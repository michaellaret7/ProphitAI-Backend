"""Amihud illiquidity premium alpha.

Amihud (2002, J. Financial Markets "Illiquidity and Stock Returns")
defined the illiquidity ratio as the average absolute daily return per
dollar of trading volume — capturing the price impact of unit
liquidity demand. Long-history evidence shows a persistent ~5%/yr
premium for high-illiquidity stocks (compensation for trading costs
and slow risk transfer).

The signal is cross-sectional: per bar, score each ticker by how much
its illiquidity exceeds the universe median. High illiquidity gets a
positive score (long candidate); deep liquidity gets negative.

    illiq_i = mean(|return_i| / dollar_volume_i) over past N bars
    score_i = illiq_i - median_universe_illiq

Distinct from ``LowVolAlpha`` and ``GarmanKlassVolAlpha`` (which
capture risk premia) — illiquidity is its own anomaly, empirically
separable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class AmihudIlliquidityAlpha(CrossSectionalAlpha):
    """Cross-sectional Amihud illiquidity score (illiq - median).

    Args:
        lookback_days: Window for the illiquidity average (default 21).
        hold_days: Informational ``close_time`` horizon.
        min_universe_size: Universe-size floor for the median.
    """

    name = "amihud"
    required_columns = ("close", "volume")

    def __init__(
        self,
        lookback_days: int = 21,
        hold_days: int = 21,
        min_universe_size: int = 5,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = lookback_days + 1

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        illiq_by_symbol: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"].iloc[-(self._window + 1):]
            volumes = df["volume"].iloc[-self._window:]
            returns = closes.pct_change().iloc[-self._window:]

            if returns.isna().any():
                continue

            dollar_volume = closes.iloc[-self._window:] * volumes

            if (dollar_volume <= 0.0).any():
                continue

            ratios = returns.abs() / dollar_volume

            illiq = float(ratios.mean())

            if not np.isfinite(illiq) or illiq <= 0.0:
                continue

            illiq_by_symbol[symbol] = illiq

        if len(illiq_by_symbol) < self._min_universe:
            return None

        median_illiq = float(np.median(list(illiq_by_symbol.values())))

        return {"illiq": illiq_by_symbol, "median": median_illiq}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        illiq_by_symbol: dict[str, float] = stats["illiq"]
        median_illiq: float = stats["median"]

        illiq = illiq_by_symbol.get(symbol)

        if illiq is None:
            return None

        # Reason: high illiq → long; subtract median so positive = above-median
        # illiquidity (long candidate). Scale by 1e9 because raw |ret|/$vol is
        # tiny; scaling preserves rank but expands numerical range for the PCM.
        return (illiq - median_illiq) * 1.0e9

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized cross-sectional Amihud illiquidity score."""
        if panel.volume is None:
            raise ValueError(
                "AmihudIlliquidityAlpha.compute_panel requires panel.volume",
            )

        closes = panel.close
        volume = panel.volume

        returns = closes.pct_change()
        dollar_volume = closes * volume

        ratios = returns.abs() / dollar_volume.where(dollar_volume > 0.0)

        illiq_panel = ratios.rolling(self._window).mean()
        illiq_panel = illiq_panel.where(illiq_panel > 0.0)

        valid_count = illiq_panel.count(axis=1)
        median_illiq = illiq_panel.median(axis=1)

        score = illiq_panel.sub(median_illiq, axis=0) * 1.0e9

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
