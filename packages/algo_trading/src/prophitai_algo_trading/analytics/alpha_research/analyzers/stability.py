"""Sub-period stability analyzer.

Splits the panel index into ``config.subperiod_count`` equal-length
slices, recomputes IC and Sharpe within each slice, and reports a
``min/max`` ratio across slices. The ratio is the headline number — an
alpha with Sharpe 1.5 in the first half and 0.2 in the second has a
ratio of ~0.13 and should be flagged.

In-sample stability check: it doesn't replace OOS validation, but it
catches alphas whose edge concentrates in one slice of history without
needing a separate test panel.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from prophitai_algo_trading.analytics.alpha_research.analyzers.ic import (
    compute_ic_series,
)


SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


#     ================================
# --> Helper funcs
#     ================================

def _equal_slices(index: pd.DatetimeIndex, count: int) -> list[slice]:
    """Return ``count`` equal-length integer slices spanning ``index``.

    Last slice absorbs any remainder so every bar is covered exactly once.
    """
    n = len(index)
    base = n // count

    slices: list[slice] = []

    for i in range(count):
        start = i * base
        end = (i + 1) * base if i < count - 1 else n
        slices.append(slice(start, end))

    return slices


def _annualized_sharpe(returns: pd.Series) -> float:
    """Annualized Sharpe of a per-bar return series, no risk-free rate."""
    clean = returns.dropna()

    if len(clean) < 2:
        return 0.0

    span_seconds = (clean.index[-1] - clean.index[0]).total_seconds()
    years = max(span_seconds / SECONDS_PER_YEAR, EPSILON)
    bars_per_year = len(clean) / years

    log_returns = np.log1p(clean)
    std = float(log_returns.std())

    if std <= EPSILON:
        return 0.0

    mean = float(log_returns.mean())

    return float(mean / std * np.sqrt(bars_per_year))


def _slice_metrics(
    bar_returns: pd.Series,
    score: pd.DataFrame,
    forward_returns: pd.DataFrame,
    bar_slice: slice,
) -> dict[str, float]:
    """IC + Sharpe + total return on a single sub-period slice."""
    return_slice = bar_returns.iloc[bar_slice]

    sharpe = _annualized_sharpe(return_slice)
    total_return = float((1.0 + return_slice.fillna(0.0)).prod() - 1.0)

    score_slice = score.iloc[bar_slice]
    forward_slice = forward_returns.iloc[bar_slice]

    per_date_ic = compute_ic_series(score_slice, forward_slice).dropna()
    ic_mean = float(per_date_ic.mean()) if not per_date_ic.empty else 0.0

    return {
        "sharpe": round(sharpe, 3),
        "ic_mean": round(ic_mean, 4),
        "total_return": round(total_return * 100.0, 2),
        "bars": int(return_slice.notna().sum()),
    }


#     ================================
# --> Public analyzer
#     ================================

def compute_subperiod_stability(
    bar_returns: pd.Series,
    score: pd.DataFrame,
    forward_returns: pd.DataFrame,
    subperiod_count: int,
    minimum_bars_per_slice: int,
) -> dict[str, Any] | None:
    """Per-slice metrics and the cross-slice min/max Sharpe ratio.

    Returns ``None`` (with the caller logging a failure reason) when
    each slice would have fewer than ``minimum_bars_per_slice`` bars.

    Args:
        bar_returns: Per-bar portfolio return series (post-cost).
        score: ``[date x ticker]`` raw alpha score.
        forward_returns: ``[date x ticker]`` forward returns at the
            primary IC horizon.
        subperiod_count: Number of equal-length slices.
        minimum_bars_per_slice: Soft floor — analyzer skips when the
            split would produce slices smaller than this.

    Returns:
        Dict with keys:
            ``slices``: list of per-slice metric dicts.
            ``sharpe_min_max_ratio``: min(sharpe) / max(sharpe). NaN if
                max <= 0; capped at 0.0 when min and max have opposite
                signs (one slice loses) — that's the meaningful "broke"
                signal.
            ``ic_min_max_ratio``: same idea for IC.

        Or ``None`` if the panel is too short to split meaningfully.
    """
    if bar_returns.empty:
        return None

    if len(bar_returns) < subperiod_count * minimum_bars_per_slice:
        return None

    slices = _equal_slices(bar_returns.index, subperiod_count)  # type: ignore[arg-type]

    per_slice: list[dict[str, float]] = []

    for bar_slice in slices:
        per_slice.append(
            _slice_metrics(bar_returns, score, forward_returns, bar_slice),
        )

    sharpes = [s["sharpe"] for s in per_slice]
    ics = [s["ic_mean"] for s in per_slice]

    sharpe_ratio = _safe_min_max_ratio(sharpes)
    ic_ratio = _safe_min_max_ratio(ics)

    return {
        "slices": per_slice,
        "sharpe_min_max_ratio": sharpe_ratio,
        "ic_min_max_ratio": ic_ratio,
    }


def _safe_min_max_ratio(values: list[float]) -> float:
    """``min/max`` ratio, with sign-disagreement clamped to 0.0.

    When min and max have opposite signs the alpha is producing wins in
    one slice and losses in another — the "broke" signal. Returning a
    naive negative ratio is misleading; clamp to 0.0 instead.
    Returns NaN when the max is non-positive (degenerate).
    """
    if not values:
        return float("nan")

    lo = min(values)
    hi = max(values)

    if hi <= 0.0:
        return float("nan")

    if lo < 0.0:
        return 0.0

    return round(lo / hi, 3)
