"""Multi-asset portfolio entity that computes risk and performance metrics."""

import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_risk_metrics import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_performance_metrics import calc_all_performance_metrics
from app.core.calc_v2.models.risk_model import RiskMetrics
from app.core.calc_v2.models.performance_model import PerformanceMetrics


class Portfolio:
    """Multi-asset portfolio entity with weighted returns, covariance, and metrics."""

    def __init__(
        self,
        name: str,
        tickers: list[str],
        weights: list[float],
        price_df: pd.DataFrame,
        benchmark_prices: pd.Series | None = None
    ):
        if len(tickers) != len(weights):
            raise ValueError("Tickers must match the amount of weights")

        self.name = name
        self.tickers = tickers
        self.weights = np.array(weights)
        self.price_df = price_df[tickers]
        self.positions = list(zip(tickers, weights))

        # Asset-level daily returns (for cov/corr matrices)
        self.asset_returns = self.price_df.pct_change().dropna()

        # Benchmark returns (calculated from prices)
        self.benchmark_returns: pd.Series | None = None
        if benchmark_prices is not None:
            self.benchmark_returns = benchmark_prices.pct_change().dropna()

        # Portfolio-level returns
        self.daily_returns = (self.asset_returns * self.weights).sum(axis=1)
        self.cumulative_returns = (1 + self.daily_returns).cumprod() - 1
        self.log_returns = np.log(1 + self.daily_returns)

        # Cross-asset covariance and correlation (uses asset-level returns)
        self.corr_matrix: pd.DataFrame = self.asset_returns.corr()
        self.cov_matrix: pd.DataFrame = self.asset_returns.cov()

        # Risk metrics (with optional benchmark for beta/tracking error)
        self.risk_metrics: RiskMetrics = calc_all_risk_metrics(
            self.daily_returns,
            self.benchmark_returns
        )

        self.performance_metrics: PerformanceMetrics = calc_all_performance_metrics(
            self.daily_returns,
            self.benchmark_returns
        )

