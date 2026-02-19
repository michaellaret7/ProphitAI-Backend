"""Correlation matrix calculations for a group of assets."""

from typing import cast

import numpy as np
import pandas as pd

from app.core.calc_v2.models.correlation_model import CorrelationMetrics


def calc_correlation_matrix(asset_returns: pd.DataFrame) -> pd.DataFrame:
    """Calculate the pairwise correlation matrix from asset daily returns."""
    return asset_returns.corr()


def calc_avg_pairwise_correlation(corr_matrix: pd.DataFrame) -> float:
    """Calculate the mean of all off-diagonal correlations.

    Higher values indicate less diversification benefit among the assets.
    """
    n = len(corr_matrix)
    if n < 2:
        return 0.0

    # Reason: np.triu_indices with k=1 selects only the upper triangle
    # (excluding the diagonal of 1s), avoiding double-counting.
    upper_indices = np.triu_indices(n, k=1)
    off_diagonal = corr_matrix.values[upper_indices]

    return float(np.mean(off_diagonal))


def calc_diversification_ratio(corr_matrix: pd.DataFrame) -> float:
    """Calculate the diversification ratio via eigenvalue entropy.

    Effective N / Actual N, where Effective N = exp(Shannon entropy of
    normalised eigenvalues). Ranges from 1/N (perfectly correlated) to
    1.0 (perfectly uncorrelated).
    """
    n = len(corr_matrix)
    if n < 2:
        return 1.0

    eigenvalues = np.linalg.eigvalsh(corr_matrix.values)
    # Reason: Numerical noise can produce tiny negative eigenvalues.
    eigenvalues = np.maximum(eigenvalues, 0.0)

    total = eigenvalues.sum()
    if total == 0:
        return 1.0

    proportions = eigenvalues / total
    # Reason: Filter zeros to avoid log(0).
    nonzero = proportions[proportions > 0]
    entropy = -np.sum(nonzero * np.log(nonzero))
    effective_n = float(np.exp(entropy))

    return effective_n / n


def calc_rolling_avg_correlation(
    asset_returns: pd.DataFrame,
    window: int = 60,
) -> pd.Series:
    """Calculate rolling average pairwise correlation over time.

    For each date, computes the correlation matrix over the trailing window,
    then averages all off-diagonal values. Detects correlation regime changes —
    rising average correlation means diversification is deteriorating.

    Args:
        asset_returns: DataFrame of daily returns (columns = tickers).
        window: Rolling window size in trading days. Default 60.
    """
    n = len(asset_returns.columns)
    if n < 2 or len(asset_returns) < window:
        return pd.Series(dtype=float)

    pair_correlations: list[pd.Series] = []

    # Reason: compute rolling correlation for each unique pair, then average.
    for i in range(n):
        for j in range(i + 1, n):
            rolling_corr = asset_returns.iloc[:, i].rolling(window).corr(
                asset_returns.iloc[:, j]
            )
            pair_correlations.append(rolling_corr)

    stacked = pd.concat(pair_correlations, axis=1)
    result = cast(pd.Series, stacked.mean(axis=1))
    return result.dropna()


def calc_all_correlation_metrics(asset_returns: pd.DataFrame) -> CorrelationMetrics:
    """Calculate all derived correlation metrics for a group of assets."""
    corr_matrix = calc_correlation_matrix(asset_returns)

    return CorrelationMetrics(
        avg_pairwise_correlation=calc_avg_pairwise_correlation(corr_matrix),
        diversification_ratio=calc_diversification_ratio(corr_matrix),
    )
