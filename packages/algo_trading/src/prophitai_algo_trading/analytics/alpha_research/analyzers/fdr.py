"""Multiple-testing correction via Benjamini-Hochberg.

When you sweep N alphas, the best-of-N IC under the null isn't ~0 — it's
several standard errors above zero just from luck. Without correction
the agent will fall in love with the lucky one every run.

The Benjamini-Hochberg procedure controls the False Discovery Rate
(expected fraction of false positives among the alphas declared
significant). At ``fdr_alpha = 0.10``, of the alphas the procedure
labels ``passes_fdr=True``, on average at most 10% are false discoveries.

P-values are computed two-sided so that "real but inverted" alphas
(strong negative IC — the signal is real, you'd just trade the opposite
direction) survive. The graduation analyzer downstream uses
``abs(ic_tstat)`` for the same reason.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


#     ================================
# --> Helper funcs
#     ================================

def _two_sided_p_from_tstat(tstat: float) -> float:
    """Two-sided p-value from a z-score under the standard normal.

    For sample sizes typical in alpha research (>>30), the t and z
    distributions are indistinguishable. Use normal for simplicity and
    speed.
    """
    return float(2.0 * (1.0 - norm.cdf(abs(tstat))))


def _benjamini_hochberg(
    p_values: np.ndarray, alpha: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Vanilla BH FDR procedure.

    Args:
        p_values: 1-D array of raw p-values.
        alpha: Target FDR level.

    Returns:
        ``(adjusted, passes)``:
            adjusted: BH-adjusted p-values (with monotonicity enforced).
            passes: Boolean array — True iff adjusted p <= alpha.
    """
    n = len(p_values)

    if n == 0:
        return np.array([]), np.array([], dtype=bool)

    order = np.argsort(p_values)
    sorted_p = p_values[order]

    ranks = np.arange(1, n + 1)
    raw_adjusted = sorted_p * n / ranks

    # Reason: BH adjusted p-values must be monotone non-decreasing in
    #         rank — enforce by taking the running min from the largest
    #         rank back to the smallest, then clipping at 1.0.
    monotone = np.minimum.accumulate(raw_adjusted[::-1])[::-1]
    monotone = np.clip(monotone, 0.0, 1.0)

    adjusted = np.empty_like(monotone)
    adjusted[order] = monotone

    passes = adjusted <= alpha

    return adjusted, passes


#     ================================
# --> Public analyzer
#     ================================

def apply_fdr_correction(
    ic_tstats: dict[str, float], alpha: float,
) -> pd.DataFrame:
    """Benjamini-Hochberg FDR correction across a sweep's IC t-stats.

    Args:
        ic_tstats: ``{alpha_name: ic_tstat}`` from the per-alpha layer.
        alpha: Target false-discovery rate (e.g., 0.10 = at most 10%
            false positives among the survivors on average).

    Returns:
        DataFrame indexed by alpha name with columns:
            ``ic_tstat``: Original t-stat (passed through).
            ``p_value``: Raw two-sided p-value.
            ``fdr_adjusted_pvalue``: BH-adjusted p-value.
            ``passes_fdr``: bool — True iff adjusted p <= alpha.
    """
    if not ic_tstats:
        return pd.DataFrame()

    names = list(ic_tstats.keys())
    tstats = np.array([ic_tstats[n] for n in names], dtype=float)

    raw_p = np.array([_two_sided_p_from_tstat(t) for t in tstats])

    adjusted, passes = _benjamini_hochberg(raw_p, alpha)

    return pd.DataFrame({
        "ic_tstat": np.round(tstats, 2),
        "p_value": np.round(raw_p, 4),
        "fdr_adjusted_pvalue": np.round(adjusted, 4),
        "passes_fdr": passes,
    }, index=pd.Index(names, name="alpha"))
