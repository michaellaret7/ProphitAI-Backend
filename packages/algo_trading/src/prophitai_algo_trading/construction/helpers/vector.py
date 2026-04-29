"""Shared helpers for vectorized portfolio constructors.

Pure ``[date x ticker]`` panel transforms — no per-bar state, no
``AlgorithmContext``. Exposed as a small toolkit so custom user PCMs
can compose them rather than re-deriving the math.

    apply_cadence            — quantize a dense weight panel to a
                               rebalance schedule (ffill between
                               rebalance dates).
    zscore_rowwise           — cross-sectional z-score per row, with
                               optional symmetric winsorization.
    rank_to_long_short_weights — quantile-cut + magnitude-weighted
                               long/short weight panel from a signed
                               score panel.

None of these are public package API — the engine and pre-built PCMs
import them internally; user PCMs that want them import explicitly.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


#     ================================
# --> Helper funcs
#     ================================

def _empty_like(panel: pd.DataFrame) -> pd.DataFrame:
    """Zero-filled DataFrame with the same shape/index/columns as ``panel``."""
    return pd.DataFrame(
        0.0, index=panel.index, columns=panel.columns,
    )


#     ================================
# --> Rebalance cadence
#     ================================

def apply_cadence(
    weights: pd.DataFrame,
    rebalance_every: timedelta | None,
) -> pd.DataFrame:
    """Quantize a dense weight panel to a rebalance schedule.

    On non-rebalance bars, the panel forward-fills from the most recent
    rebalance bar's weights. ``rebalance_every=None`` returns the input
    unchanged (every bar is a rebalance bar).

    Args:
        weights: Dense ``[date x ticker]`` weight panel produced by a
            PCM's pre-cadence sizing logic.
        rebalance_every: Minimum elapsed time between rebalances. The
            first bar always counts as a rebalance.

    Returns:
        A new DataFrame of the same shape with non-rebalance rows
        ffilled from the prior rebalance row.
    """
    if rebalance_every is None or weights.empty:
        return weights.copy()

    if rebalance_every <= timedelta(0):
        raise ValueError("rebalance_every must be positive")

    index = weights.index

    rebalance_mask = pd.Series(False, index=index)
    rebalance_mask.iloc[0] = True

    last_rebalance = index[0]

    for ts in index[1:]:
        if (ts - last_rebalance) >= rebalance_every:
            rebalance_mask.loc[ts] = True
            last_rebalance = ts

    sparse = weights.where(rebalance_mask, other=np.nan)

    return sparse.ffill().fillna(0.0)


#     ================================
# --> Cross-sectional z-score
#     ================================

def zscore_rowwise(
    panel: pd.DataFrame,
    winsor_at: float | None = 3.0,
    min_count: int = 3,
) -> pd.DataFrame:
    """Per-row cross-sectional z-score with optional symmetric winsorization.

    Rows with fewer than ``min_count`` non-NaN values, or zero
    cross-sectional variance, collapse to all zeros — no false signal
    on degenerate days.

    Args:
        panel: ``[date x ticker]`` score panel.
        winsor_at: Symmetric clip applied after z-scoring. ``None``
            disables winsorization.
        min_count: Minimum non-NaN values per row to compute a z-score.

    Returns:
        Z-scored DataFrame, same shape, NaN replaced with 0.0.
    """
    if panel.empty:
        return panel.copy()

    counts = panel.count(axis=1)
    means = panel.mean(axis=1)
    stds = panel.std(axis=1, ddof=1)

    valid = (counts >= min_count) & (stds > 0.0) & stds.notna()

    z = panel.sub(means, axis=0).div(stds.replace(0.0, np.nan), axis=0)

    z = z.where(valid, other=0.0)

    z = z.fillna(0.0)

    if winsor_at is not None:
        z = z.clip(lower=-winsor_at, upper=winsor_at)

    return z


#     ================================
# --> Quantile-cut long/short sizing
#     ================================

def rank_to_long_short_weights(
    scores: pd.DataFrame,
    quantile: float = 0.10,
    gross_exposure: float = 2.0,
    per_position_cap: float = 0.10,
    min_abs_score: float = 0.0,
) -> pd.DataFrame:
    """Build dollar-neutral long/short weights from a signed score panel.

    Per row:
        1. Rank tickers by signed score.
        2. Take top ``quantile`` as longs, bottom ``quantile`` as shorts.
        3. Drop names with ``|signed_score| < min_abs_score``.
        4. Within each side, weight proportional to ``|signed_score|``.
        5. Each side targets ``gross_exposure / 2``; per-position cap
           applied; sides rescaled to the smaller side so the row is
           dollar-neutral.

    On rows where one side is empty after thresholding, the row is
    all zeros.

    Args:
        scores: Signed score panel.
        quantile: Fraction of the row taken per side (0.10 = decile cut).
        gross_exposure: Total long+short absolute weight target per row.
        per_position_cap: Maximum unsigned weight per ticker per row.
        min_abs_score: Threshold — names below this in absolute score
            are dropped before quantile cutting.

    Returns:
        ``[date x ticker]`` signed weight panel.
    """
    if not 0.0 < quantile <= 0.5:
        raise ValueError("quantile must be in (0, 0.5]")
    if gross_exposure <= 0:
        raise ValueError("gross_exposure must be > 0")
    if not 0.0 < per_position_cap <= 1.0:
        raise ValueError("per_position_cap must be in (0, 1]")

    if scores.empty:
        return scores.copy()

    weights = _empty_like(scores)

    side_budget = gross_exposure / 2.0

    score_arr = scores.to_numpy(dtype=float, copy=True)
    weight_arr = np.zeros_like(score_arr)

    # Reason: thresholding zeroes out subthreshold scores so rank-based
    # quantile cutting only sees actionable names; leaves quantile sizing
    # vectorized cleanly.
    if min_abs_score > 0.0:
        below = np.abs(score_arr) < min_abs_score
        score_arr[below] = np.nan

    n_rows = score_arr.shape[0]

    for row_idx in range(n_rows):
        row = score_arr[row_idx]

        finite_mask = np.isfinite(row)
        n_valid = int(finite_mask.sum())

        if n_valid == 0:
            continue

        k = max(1, int(n_valid * quantile))

        valid_idx = np.where(finite_mask)[0]
        valid_scores = row[valid_idx]

        order = np.argsort(valid_scores)

        short_local = order[:k]
        long_local = order[-k:]

        short_idx = valid_idx[short_local]
        long_idx = valid_idx[long_local]

        long_scores = row[long_idx]
        short_scores = row[short_idx]

        if (long_scores <= 0).all() or (short_scores >= 0).all():
            continue

        long_mask = long_scores > 0
        short_mask = short_scores < 0

        if not long_mask.any() or not short_mask.any():
            continue

        long_idx = long_idx[long_mask]
        short_idx = short_idx[short_mask]

        long_scores = long_scores[long_mask]
        short_scores = short_scores[short_mask]

        long_w = _side_weights(long_scores, side_budget, per_position_cap)
        short_w = _side_weights(np.abs(short_scores), side_budget, per_position_cap)

        long_sum = long_w.sum()
        short_sum = short_w.sum()

        neutral = min(long_sum, short_sum)

        if neutral <= 0.0:
            continue

        long_w = long_w * (neutral / long_sum)
        short_w = short_w * (neutral / short_sum)

        weight_arr[row_idx, long_idx] = long_w
        weight_arr[row_idx, short_idx] = -short_w

    weights[:] = weight_arr

    return weights


def _side_weights(
    abs_scores: np.ndarray,
    side_budget: float,
    per_position_cap: float,
) -> np.ndarray:
    """Magnitude-proportional weights for one side, capped per name."""
    total = abs_scores.sum()

    if total <= 0.0:
        return np.zeros_like(abs_scores)

    raw = side_budget * (abs_scores / total)

    return np.minimum(raw, per_position_cap)
