from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd


from backend.src.calculations_v2.risk.calculator import RiskCalculator


class CorrelationAnalysis:
    """Correlation and covariance utilities for portfolio analysis.

    Delegates base correlation/covariance to RiskCalculator to avoid duplication.
    """

    # Single source of truth for correlation/covariance
    correlation_matrix = staticmethod(RiskCalculator.correlation_matrix)
    covariance_matrix = staticmethod(RiskCalculator.covariance_matrix)

    @staticmethod
    def correlation_distance_matrix(corr: pd.DataFrame) -> pd.DataFrame:
        """Convert correlation matrix to distance matrix: d_ij = sqrt(0.5 * (1 - rho_ij))."""
        if corr is None or corr.empty:
            return pd.DataFrame()
        rho = corr.values
        d = np.sqrt(0.5 * (1 - rho))
        return pd.DataFrame(d, index=corr.index, columns=corr.columns)

    @staticmethod
    def hierarchical_linkage(distance_matrix: pd.DataFrame, method: str = "average"):
        """Return scipy linkage from a distance matrix."""
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform

        if distance_matrix is None or distance_matrix.empty:
            return None
        condensed = squareform(distance_matrix.values, checks=False)
        return linkage(condensed, method=method)

    @staticmethod
    def order_by_clustering(corr: pd.DataFrame, method: str = "average") -> list[str]:
        """Return a dendrogram order of tickers based on correlation clustering."""
        from scipy.cluster.hierarchy import leaves_list

        dist = CorrelationAnalysis.correlation_distance_matrix(corr)
        Z = CorrelationAnalysis.hierarchical_linkage(dist, method=method)
        if Z is None:
            return list(corr.columns)
        order = leaves_list(Z)
        return list(corr.columns[order])

    # ------------------ Portfolio-specific correlation metrics ------------------ #
    @staticmethod
    def effective_diversification_ratio(corr: pd.DataFrame) -> float:
        """Effective diversification ratio (1 / average absolute correlation)."""
        if corr is None or corr.empty:
            return 0.0
        c = corr.values
        n = c.shape[0]
        # Exclude diagonal by using upper triangle indices
        iu = np.triu_indices(n, k=1)
        vals = np.abs(c[iu])
        mean_abs = float(vals.mean()) if vals.size > 0 else 0.0
        return float(0.0 if mean_abs == 0 else 1.0 / mean_abs)

    @staticmethod
    def concentration_risk_metrics(corr: pd.DataFrame) -> dict[str, float]:
        """Return simple concentration metrics derived from correlation.

        - avg_abs_corr: mean of absolute off-diagonal correlations
        - max_abs_corr: maximum absolute pairwise correlation
        - min_abs_corr: minimum absolute pairwise correlation
        """
        if corr is None or corr.empty:
            return {"avg_abs_corr": 0.0, "max_abs_corr": 0.0, "min_abs_corr": 0.0}
        c = corr.values
        n = c.shape[0]
        iu = np.triu_indices(n, k=1)
        vals = np.abs(c[iu])
        if vals.size == 0:
            return {"avg_abs_corr": 0.0, "max_abs_corr": 0.0, "min_abs_corr": 0.0}
        return {
            "avg_abs_corr": float(vals.mean()),
            "max_abs_corr": float(vals.max()),
            "min_abs_corr": float(vals.min()),
        }

    @staticmethod
    def correlation_risk_contribution(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
        """Component variance contributions using covariance matrix.

        Returns a series where each value is w_i * (Sigma w)_i.
        """
        if weights is None or cov is None or cov.empty:
            return pd.Series(dtype=float)
        # Align order
        common = [t for t in weights.index if t in cov.index]
        if not common:
            return pd.Series(dtype=float)
        w = weights.loc[common].astype(float)
        Sigma = cov.loc[common, common].astype(float).values
        contrib = w.values * (Sigma @ w.values)
        return pd.Series(contrib, index=common)

    @staticmethod
    def pairwise_correlation_analysis(returns_df: pd.DataFrame) -> pd.DataFrame:
        """Return a tidy DataFrame of pairwise correlations with (i, j, rho, |rho|), upper triangle only.

        Columns: asset_i, asset_j, correlation, abs_correlation
        """
        if returns_df is None or returns_df.empty:
            return pd.DataFrame(columns=["asset_i", "asset_j", "correlation", "abs_correlation"])  # empty tidy frame
        corr = CorrelationAnalysis.correlation_matrix(returns_df)
        if corr.empty:
            return pd.DataFrame(columns=["asset_i", "asset_j", "correlation", "abs_correlation"])  # empty tidy frame
        tickers = list(corr.columns)
        n = len(tickers)
        records = []
        for i in range(n):
            for j in range(i + 1, n):
                rho = float(corr.iat[i, j])
                records.append({
                    "asset_i": tickers[i],
                    "asset_j": tickers[j],
                    "correlation": rho,
                    "abs_correlation": abs(rho),
                })
        return pd.DataFrame.from_records(records, columns=["asset_i", "asset_j", "correlation", "abs_correlation"])

    @staticmethod
    def herfindahl_concentration_index(weights: pd.Series) -> float:
        """Herfindahl concentration index - sum of squared weights. Effective number of assets = 1/HHI."""
        if weights.empty:
            return np.nan
        return float(np.sum(weights.values ** 2))




