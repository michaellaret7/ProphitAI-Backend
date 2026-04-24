"""Cointegration pair-trading alpha (stat arb).

Classic Engle-Granger-style pairs trade on a pre-specified list of
ticker pairs. For each pair (A, B):

    1. Estimate hedge ratio β via OLS on log prices over the lookback
       window:
           log(A_t) = α + β · log(B_t) + ε_t
    2. Compute the residual series ε_t = log(A) - α - β · log(B).
    3. Score = -z_score(ε_today)
           = -(ε_today - mean(ε)) / std(ε)

The sign flip on the z-score is the mean-reversion assumption: if the
spread is elevated (ε large and positive), A is rich vs. B → short A,
long B. Because ``PairAlpha`` treats positive score as "long A / short
B," negating z-score aligns that convention with the mean-reversion
bet.

The magnitude of the z-score is clipped at ``max_z`` so runaway spreads
(where cointegration has likely broken) don't emit oversized signals.

Each firing pair emits TWO Insights — long leg + short leg — with the
same magnitude so the PCM sees a dollar-neutral signal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alphas.base import PairAlpha

if TYPE_CHECKING:
    import pandas as pd


#     ================================
# --> Helper funcs
#     ================================

def _spread_zscore(
    log_a: np.ndarray, log_b: np.ndarray,
) -> tuple[float, float]:
    """OLS-hedged log-price spread z-score at the last observation.

    Returns (z_score, residual_std). Caller can detect a degenerate
    series by checking ``residual_std <= 0``.
    """
    ones = np.ones_like(log_b)
    design = np.column_stack([ones, log_b])

    # Reason: lstsq is numerically stable vs. manual (X'X)^-1 X'y.
    coef, *_ = np.linalg.lstsq(design, log_a, rcond=None)

    alpha = float(coef[0])
    beta = float(coef[1])

    residuals = log_a - alpha - beta * log_b

    mean_e = float(np.mean(residuals))
    std_e = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0

    if std_e <= 0.0 or not np.isfinite(std_e):
        return 0.0, 0.0

    z = (float(residuals[-1]) - mean_e) / std_e

    return z, std_e


#     ================================
# --> Alpha
#     ================================

class CointegrationPairAlpha(PairAlpha):
    """Mean-reversion z-score on OLS-hedged log-price spreads.

    Args:
        pairs: List of ``(sym_a, sym_b)`` tuples — order matters.
            Positive score => long A / short B.
        lookback_days: Bars used for the hedge ratio + spread stats.
        hold_days: ``close_time`` horizon. Pair reversions typically
            play out over 1-4 weeks — default 10.
        entry_z: Minimum |z-score| to emit a signal. Below this, the
            pair is "in-band" and the alpha stays silent (score = None).
        max_z: Clip absolute z-score at this value so a broken pair
            doesn't emit runaway magnitudes. Default 4.0.
    """

    name = "cointegration_pair"

    def __init__(
        self,
        pairs: list[tuple[str, str]],
        lookback_days: int = 60,
        hold_days: int = 10,
        entry_z: float = 2.0,
        max_z: float = 4.0,
    ):
        if not pairs:
            raise ValueError("CointegrationPairAlpha requires at least one pair")

        if entry_z < 0.0:
            raise ValueError("entry_z must be >= 0")

        if max_z <= entry_z:
            raise ValueError("max_z must be greater than entry_z")

        self.pairs = list(pairs)
        self.lookback = lookback_days
        self.hold_days = hold_days
        self._entry_z = entry_z
        self._max_z = max_z

    def compute_pair_score(
        self, df_a: "pd.DataFrame", df_b: "pd.DataFrame",
    ) -> float | None:
        # Reason: common bars only — misaligned indices produce bogus
        # regressions. Intersect on index, take the trailing window.
        joined = df_a[["close"]].join(
            df_b[["close"]], how="inner", lsuffix="_a", rsuffix="_b",
        )

        if len(joined) < self.lookback:
            return None

        window = joined.iloc[-self.lookback:]

        closes_a = window["close_a"].to_numpy(dtype=float)
        closes_b = window["close_b"].to_numpy(dtype=float)

        if (closes_a <= 0.0).any() or (closes_b <= 0.0).any():
            return None

        log_a = np.log(closes_a)
        log_b = np.log(closes_b)

        z, std_e = _spread_zscore(log_a, log_b)

        if std_e <= 0.0:
            return None

        # Reason: in-band → no trade. Below entry threshold, the pair
        # is close enough to equilibrium that the reversion edge is
        # weak after costs.
        if abs(z) < self._entry_z:
            return None

        # Reason: clip runaway z so a structurally broken pair doesn't
        # emit an absurd magnitude.
        clipped = max(-self._max_z, min(self._max_z, z))

        # Reason: negate — positive z (A rich vs. B) means short A /
        # long B, which is direction_a = -1 under PairAlpha's
        # "positive score = long A" convention.
        return -clipped
