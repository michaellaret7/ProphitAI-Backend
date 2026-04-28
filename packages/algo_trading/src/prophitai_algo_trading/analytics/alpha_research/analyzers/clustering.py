"""Hierarchical clustering of alphas by return correlation.

Converts the N x N correlation matrix into a ``1 - |corr|`` distance
matrix (so highly correlated AND anti-correlated alphas are both
treated as the same signal — anti-correlation is just sign-flipped
exposure to the same factor) and runs scipy agglomerative clustering
with average linkage.

Cuts the dendrogram at ``cluster_distance_threshold`` so alphas with
``|corr| >= 1 - threshold`` end up in the same cluster. Default
threshold of 0.30 → alphas with ``|corr| >= 0.70`` cluster together,
which matches typical "they're the same factor" thresholds in the
literature.

The clustering output drives two consumer-side decisions:
  1. The agent recommends "one survivor per cluster" instead of
     eyeballing a 30 x 30 correlation matrix.
  2. The graduation analyzer can flag clusters where multiple alphas
     pass — they're redundant.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform


EPSILON = 1e-9


#     ================================
# --> Helper funcs
#     ================================

def _correlation_to_distance(correlations: pd.DataFrame) -> np.ndarray:
    """Convert correlation matrix to a condensed distance vector.

    Distance is ``1 - |corr|`` — symmetric in sign, so anti-correlated
    alphas group with their mirror image. The diagonal is forced to
    zero (handles tiny floating-point drift from ``corr()``).
    """
    distance_matrix = 1.0 - correlations.abs().to_numpy()
    np.fill_diagonal(distance_matrix, 0.0)

    # Reason: linkage requires non-negative distances; clip any tiny
    #         negatives that fall out of floating-point arithmetic.
    distance_matrix = np.clip(distance_matrix, 0.0, None)

    # Reason: scipy expects a 1-D condensed distance vector (upper
    #         triangle, no diagonal) rather than the full matrix.
    return squareform(distance_matrix, checks=False)


#     ================================
# --> Public analyzer
#     ================================

def cluster_by_correlation(
    correlations: pd.DataFrame, distance_threshold: float,
) -> tuple[dict[int, list[str]], np.ndarray]:
    """Hierarchical agglomerative clustering of alphas.

    Args:
        correlations: N x N return-correlation DataFrame from
            ``build_return_correlations``.
        distance_threshold: Cut height. Alphas with pairwise distance
            ``<= threshold`` (i.e., ``|corr| >= 1 - threshold``) end up
            in the same cluster.

    Returns:
        ``(clusters, linkage_matrix)``:
            clusters: ``{cluster_id: [alpha_names...]}``.
            linkage_matrix: scipy linkage output for plotting / further
                analysis. Empty array when N < 2.
    """
    if correlations.empty or len(correlations.columns) < 2:
        return {}, np.empty((0, 4))

    names = list(correlations.columns)

    condensed = _correlation_to_distance(correlations)

    linkage_matrix = linkage(condensed, method="average")

    cluster_ids = fcluster(
        linkage_matrix, t=distance_threshold, criterion="distance",
    )

    clusters: dict[int, list[str]] = {}

    for name, cid in zip(names, cluster_ids):
        clusters.setdefault(int(cid), []).append(name)

    return clusters, linkage_matrix
