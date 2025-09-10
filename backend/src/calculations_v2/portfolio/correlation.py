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
        c = corr.copy().astype(float)
        # Fill any missing correlations with 0.0 to maintain a valid distance structure
        c = c.fillna(0.0)
        # Ensure exact 1.0 on diagonal, clip numerical drift to [-1, 1]
        np.fill_diagonal(c.values, 1.0)
        rho = np.clip(c.values, -1.0, 1.0)
        d = np.sqrt(0.5 * (1.0 - rho))
        # Distance of an item to itself is zero
        np.fill_diagonal(d, 0.0)
        return pd.DataFrame(d, index=c.index, columns=c.columns)

    @staticmethod
    def hierarchical_linkage(distance_matrix: pd.DataFrame, method: str = "average"):
        """Return scipy linkage from a symmetric distance matrix (not for 'ward')."""
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform

        if distance_matrix is None or distance_matrix.empty:
            return None
        if method == "ward":
            raise ValueError("Ward linkage requires Euclidean distances on observations, not a precomputed correlation distance.")
        dm = distance_matrix.astype(float).values
        # Enforce symmetry and zero diagonal for safety
        dm = (dm + dm.T) / 2.0
        np.fill_diagonal(dm, 0.0)
        condensed = squareform(dm, checks=False)
        return linkage(condensed, method=method)

    @staticmethod
    def order_by_clustering(corr: pd.DataFrame, method: str = "average") -> list[str]:
        """Return a dendrogram order of tickers based on correlation clustering."""
        from scipy.cluster.hierarchy import leaves_list
        if corr is None or corr.empty:
            return []
        dist = CorrelationAnalysis.correlation_distance_matrix(corr)
        Z = CorrelationAnalysis.hierarchical_linkage(dist, method=method)
        if Z is None:
            return list(corr.columns)
        order = leaves_list(Z)
        return list(corr.columns[order])

    # ------------------ Portfolio-specific correlation metrics ------------------ #
    @staticmethod
    def effective_diversification_ratio(corr: pd.DataFrame) -> float:
        """Inverse mean absolute off-diagonal correlation (heuristic)."""
        if corr is None or corr.empty or corr.shape[0] < 2:
            return np.nan
        c = corr.values.astype(float)
        n = c.shape[0]
        iu = np.triu_indices(n, k=1)
        vals = np.abs(c[iu])
        if vals.size == 0:
            return np.nan
        mean_abs = float(np.nanmean(vals))
        if not np.isfinite(mean_abs):
            return np.nan
        return np.inf if mean_abs == 0.0 else float(1.0 / mean_abs)

    @staticmethod
    def concentration_risk_metrics(corr: pd.DataFrame) -> dict[str, float]:
        """Return simple concentration metrics derived from correlation.

        - avg_abs_corr: mean of absolute off-diagonal correlations
        - max_abs_corr: maximum absolute pairwise correlation
        - min_abs_corr: minimum absolute pairwise correlation
        """
        if corr is None or corr.empty or corr.shape[0] < 2:
            return {"avg_abs_corr": np.nan, "max_abs_corr": np.nan, "min_abs_corr": np.nan}
        c = corr.values.astype(float)
        n = c.shape[0]
        iu = np.triu_indices(n, k=1)
        vals = np.abs(c[iu])
        if vals.size == 0:
            return {"avg_abs_corr": np.nan, "max_abs_corr": np.nan, "min_abs_corr": np.nan}
        return {
            "avg_abs_corr": float(np.nanmean(vals)),
            "max_abs_corr": float(np.nanmax(vals)),
            "min_abs_corr": float(np.nanmin(vals)),
        }

    @staticmethod
    def correlation_risk_contribution(weights: pd.Series, cov: pd.DataFrame, as_percent: bool = False) -> pd.Series:
        """Component variance contributions c_i = w_i * (Σ w)_i; optional % of total variance."""
        if weights is None or cov is None or cov.empty or weights.empty:
            return pd.Series(dtype=float)
        # Align order
        common = [t for t in weights.index if t in cov.index]
        if not common:
            return pd.Series(dtype=float)
        w = weights.loc[common].astype(float)
        Sigma = cov.loc[common, common].astype(float).values
        vec = Sigma @ w.values
        contrib = w.values * vec  # component variance
        s = pd.Series(contrib, index=common)
        if as_percent:
            total_var = float(w.values @ vec)
            return s / total_var if total_var != 0 else (s * np.nan)
        return s

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
    def herfindahl_concentration_index(weights: pd.Series, gross_normalize: bool = True) -> float:
        """HHI = sum(w_i^2). For long/short, set gross_normalize=True to use |w| / sum|w|."""
        if weights is None or weights.empty:
            return np.nan
        w = weights.astype(float)
        if gross_normalize:
            denom = np.abs(w).sum()
            if denom == 0:
                return np.nan
            w = np.abs(w) / denom
        # else: assumes long-only or already normalized to sum to 1
        return float(np.sum(np.square(w.values)))




