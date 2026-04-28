"""Cross-alpha return-correlation analyzers.

Two pure functions consumed by the cross-alpha layer in ``runner.py``:

    build_return_correlations: Pearson correlation matrix of per-alpha
        bar-return series — the multi-alpha independence diagnostic.
    top_correlations_for: Per-alpha projection — name's K most-correlated
        peers, sorted by absolute correlation.
"""

from __future__ import annotations

import pandas as pd


#     ================================
# --> Helper funcs
#     ================================

def _correlation_frame(
    bar_returns_map: dict[str, pd.Series],
) -> pd.DataFrame:
    """Wide DataFrame of per-alpha bar-returns, aligned on the union index."""
    return pd.DataFrame(bar_returns_map)


#     ================================
# --> Public analyzers
#     ================================

def build_return_correlations(
    bar_returns_map: dict[str, pd.Series],
) -> pd.DataFrame:
    """Pairwise Pearson correlation of per-alpha bar-return series.

    Uses the union of indices; missing values become NaN and pandas
    handles them pairwise. Returns an empty DataFrame when fewer than
    two alphas are supplied.

    Args:
        bar_returns_map: ``{alpha_name: bar_returns_series}``.

    Returns:
        Symmetric correlation DataFrame, or empty DataFrame if N < 2.
    """
    if len(bar_returns_map) < 2:
        return pd.DataFrame()

    return _correlation_frame(bar_returns_map).corr()


def top_correlations_for(
    name: str, correlations: pd.DataFrame, k: int,
) -> list[tuple[str, float]]:
    """``name``'s ``k`` most-correlated peers, sorted by absolute correlation.

    Self-correlation (1.0 with itself) is dropped. NaN correlations are
    dropped. Result is sorted by absolute value descending, with the
    signed correlation reported.

    Args:
        name: Alpha to look up.
        correlations: Output of ``build_return_correlations``.
        k: Number of peers to return.

    Returns:
        List of ``(peer_name, correlation)`` tuples — empty if ``name``
        is not in the matrix or no peers have a finite correlation.
    """
    if correlations.empty or name not in correlations.columns:
        return []

    row = correlations[name].drop(labels=[name], errors="ignore").dropna()

    if row.empty:
        return []

    sorted_peers = row.reindex(row.abs().sort_values(ascending=False).index)

    top = sorted_peers.head(k)

    return [(peer, round(float(value), 4)) for peer, value in top.items()]
