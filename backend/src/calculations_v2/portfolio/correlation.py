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

if __name__ == "__main__":
    # Quick test: fetch returns for a few tickers and compute correlation analytics
    from datetime import datetime, timedelta
    from backend.src.calculations_v2.core import DataService

    ds = DataService()
    end = datetime.now()
    start = end - timedelta(days=365)
    tickers = ["AAPL", "MSFT", "SPY"]

    prices = ds.get_bulk_close_series(tickers, start, end)
    returns = pd.DataFrame(prices).pct_change(fill_method=None).dropna()

    corr = CorrelationAnalysis.correlation_matrix(returns)
    cov_a = CorrelationAnalysis.covariance_matrix(returns, annualize=True)
    dist = CorrelationAnalysis.correlation_distance_matrix(corr)
    Z = CorrelationAnalysis.hierarchical_linkage(dist)
    order = CorrelationAnalysis.order_by_clustering(corr)

    pd.set_option('display.width', 120)
    pd.set_option('display.max_columns', 20)
    print("tickers:", tickers)
    print("\nCorrelation matrix:")
    print(corr.round(4))
    print("\nAnnualized covariance matrix:")
    print(cov_a.round(6))
    print("\nCorrelation distance matrix:")
    print(dist.round(4))
    print("\nClustering order:", order)


