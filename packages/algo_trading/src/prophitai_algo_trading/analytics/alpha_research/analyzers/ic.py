"""Information-Coefficient analyzers.

Three pure functions, all consuming a score panel + forward-return
panel(s):

    compute_ic_series:    [date] Spearman IC — one rank-correlation per
                          bar. Foundation for the other two.
    compute_ic_decay:     mean IC at each configured horizon.
    compute_ic_rolling:   rolling-window IC for stability / regime work.

Spearman IC is implemented as Pearson on row-wise ranks — same NumPy
ops as the original ``_compute_ic`` in ``alpha_isolation.py``, just
factored so every consumer reuses the per-date series instead of
recomputing it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


EPSILON = 1e-9


#     ================================
# --> Helper funcs
#     ================================

def _spearman_per_date(
    score: pd.DataFrame, forward_returns: pd.DataFrame,
) -> pd.Series:
    """Per-date Spearman rank correlation of ``score`` vs ``forward_returns``.

    Implements Spearman as Pearson on row-wise ranks — vectorized across
    the whole panel. Returns NaN for dates where rank dispersion is zero
    on either side (constant scores or constant returns within the row).
    """
    aligned_score = score.reindex_like(forward_returns)

    ranked_score = aligned_score.rank(axis=1)
    ranked_ret = forward_returns.rank(axis=1)

    sx = ranked_score.sub(ranked_score.mean(axis=1), axis=0)
    sy = ranked_ret.sub(ranked_ret.mean(axis=1), axis=0)

    numer = (sx * sy).sum(axis=1)
    denom = np.sqrt((sx ** 2).sum(axis=1) * (sy ** 2).sum(axis=1))

    valid = denom > 0.0

    per_date = pd.Series(
        np.where(valid, numer / denom.where(valid, 1.0), np.nan),
        index=aligned_score.index,
    )

    return per_date


def _tstat_from_series(per_date_ic: pd.Series) -> float:
    """T-statistic of a per-date IC series — mean / standard error."""
    clean = per_date_ic.dropna()

    if clean.empty or len(clean) < 2:
        return 0.0

    mean = float(clean.mean())
    std = float(clean.std(ddof=1))

    if std <= 0.0:
        return 0.0

    return float(mean / (std / np.sqrt(len(clean))))


#     ================================
# --> Public analyzers
#     ================================

def compute_ic_series(
    score: pd.DataFrame, forward_returns: pd.DataFrame,
) -> pd.Series:
    """Per-date Spearman IC series.

    Foundation primitive — every other IC analyzer consumes this. Drops
    no rows; NaNs mark degenerate dates (constant scores or returns).

    Args:
        score: ``[date x ticker]`` raw alpha score panel.
        forward_returns: ``[date x ticker]`` forward asset returns —
            typically ``close.pct_change(h).shift(-h)``.

    Returns:
        ``pd.Series`` indexed by date with one IC value per bar.
    """
    if score.empty or forward_returns.empty:
        return pd.Series(dtype=float)

    return _spearman_per_date(score, forward_returns)


def summarize_ic(per_date_ic: pd.Series) -> tuple[float, float, float]:
    """Collapse a per-date IC series into headline scalars.

    Args:
        per_date_ic: Output of ``compute_ic_series``.

    Returns:
        Tuple ``(mean_ic, ic_tstat, ic_hit_rate)``. ``hit_rate`` is the
        fraction of valid bars with IC > 0.
    """
    clean = per_date_ic.dropna()

    if clean.empty:
        return 0.0, 0.0, 0.0

    mean_ic = float(clean.mean())
    tstat = _tstat_from_series(clean)
    hit_rate = float((clean > 0.0).mean())

    return mean_ic, tstat, hit_rate


def compute_ic_decay(
    score: pd.DataFrame,
    forward_returns_by_horizon: dict[int, pd.DataFrame],
    minimum_bars_factor: int = 2,
) -> tuple[dict[int, float | None], dict[int, float | None]]:
    """Mean IC and t-stat at each configured horizon.

    A horizon is skipped (returns ``None``) when the score panel has
    fewer than ``minimum_bars_factor * h`` valid (non-NaN) bars after
    the forward shift — under that floor the IC mean / t-stat aren't
    statistically meaningful.

    Args:
        score: ``[date x ticker]`` raw alpha score.
        forward_returns_by_horizon: ``{h: forward_return_panel}`` —
            typically ``AnalyticsFacts.forward_returns_by_horizon``.
        minimum_bars_factor: Multiplier for the per-horizon insufficiency
            check. Default 2 — horizon h needs at least 2h valid bars.

    Returns:
        ``(decay_mean, decay_tstat)`` — both ``{horizon: value or None}``.
    """
    decay_mean: dict[int, float | None] = {}
    decay_tstat: dict[int, float | None] = {}

    for horizon, forward in forward_returns_by_horizon.items():
        per_date = compute_ic_series(score, forward).dropna()

        if len(per_date) < minimum_bars_factor * horizon:
            decay_mean[horizon] = None
            decay_tstat[horizon] = None
            continue

        decay_mean[horizon] = float(per_date.mean())
        decay_tstat[horizon] = _tstat_from_series(per_date)

    return decay_mean, decay_tstat


def compute_ic_rolling(
    per_date_ic: pd.Series, window: int,
) -> pd.Series:
    """Rolling-window mean IC for stability / regime diagnostics.

    Args:
        per_date_ic: Output of ``compute_ic_series``.
        window: Rolling window length in bars.

    Returns:
        Rolling mean of the IC series — same index, NaN for the warmup
        portion. Empty Series when the input is too short.
    """
    if per_date_ic.empty or len(per_date_ic) < window:
        return pd.Series(dtype=float, index=per_date_ic.index)

    return per_date_ic.rolling(window=window, min_periods=window).mean()
