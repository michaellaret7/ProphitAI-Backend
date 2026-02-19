"""Multi-asset portfolio entity that computes risk and performance metrics."""

import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_all import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_all import calc_all_performance_metrics
from app.core.calc_v2.models.risk import RiskMetrics
from app.core.calc_v2.models.performance import PerformanceMetrics
from app.core.calc_v2.models.correlation import CorrelationMetrics
from app.core.calc_v2.models.covariance import CovarianceMetrics
from app.core.calc_v2.portfolio_analytics.group_metrics import (
    fetch_ticker_classifications,
    calc_group_metrics,
    calc_net_exposure,
    calc_gross_exposure,
    calc_long_exposure,
    calc_short_exposure,
)
from app.core.calc_v2.portfolio_analytics.calc_correlation import (
    calc_correlation_matrix,
    calc_all_correlation_metrics,
    calc_rolling_avg_correlation,
)
from app.core.calc_v2.portfolio_analytics.calc_covariance import calc_covariance_matrix, calc_all_covariance_metrics
from app.core.calc_v2.portfolio_analytics.factor_exposures import calc_portfolio_factor_exposure
from app.core.calc_v2.models.factors import PortfolioFactorExposure, TickerFactors


class Portfolio:
    """Multi-asset portfolio entity with weighted returns, covariance, and metrics."""

    def __init__(
        self,
        name: str,
        tickers: list[str],
        weights: list[float],
        price_df: pd.DataFrame,
        benchmark_prices: pd.Series | None = None,
        ticker_factors: dict[str, TickerFactors] | None = None,
        universe_factors: dict[str, TickerFactors] | None = None,
    ):
        if len(tickers) != len(weights):
            raise ValueError("Tickers must match the amount of weights")
        if len(tickers) != len(set(tickers)):
            dupes = [t for t in tickers if tickers.count(t) > 1]
            raise ValueError(f"Duplicate tickers not allowed — consolidate weights instead: {set(dupes)}")
        if ticker_factors is not None and universe_factors is None:
            raise ValueError("universe_factors is required when ticker_factors is provided")

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

        # Cross-asset matrices (raw DataFrames + derived metrics)
        self.corr_matrix: pd.DataFrame = calc_correlation_matrix(self.asset_returns)
        self.cov_matrix: pd.DataFrame = calc_covariance_matrix(self.asset_returns)

        self.correlation_metrics: CorrelationMetrics = calc_all_correlation_metrics(self.asset_returns)
        self.covariance_metrics: CovarianceMetrics = calc_all_covariance_metrics(
            self.asset_returns, self.tickers, self.weights
        )

        # Risk metrics (with optional benchmark for beta/tracking error)
        self.risk_metrics: RiskMetrics = calc_all_risk_metrics(
            self.daily_returns,
            self.benchmark_returns
        )

        self.performance_metrics: PerformanceMetrics = calc_all_performance_metrics(
            self.daily_returns,
            self.benchmark_returns
        )

        # Portfolio exposure metrics
        self.net_exposure: float = calc_net_exposure(self.weights)
        self.gross_exposure: float = calc_gross_exposure(self.weights)
        self.long_exposure: float = calc_long_exposure(self.weights)
        self.short_exposure: float = calc_short_exposure(self.weights)

        # Rolling average pairwise correlation (regime detection)
        self.rolling_avg_correlation: pd.Series = calc_rolling_avg_correlation(self.asset_returns)

        # Classification-based group metrics (VaR + concentration by sector/industry/sub_industry)
        classifications = fetch_ticker_classifications(self.tickers)

        self.sector_metrics = calc_group_metrics(
            'sector', classifications, self.tickers, self.weights, self.asset_returns
        )
        self.industry_metrics = calc_group_metrics(
            'industry', classifications, self.tickers, self.weights, self.asset_returns
        )
        self.sub_industry_metrics = calc_group_metrics(
            'sub_industry', classifications, self.tickers, self.weights, self.asset_returns
        )

        # Factor exposure (optional — requires pre-computed ticker + universe factors)
        self.factor_exposure: PortfolioFactorExposure | None = None
        if ticker_factors is not None and universe_factors is not None:
            weight_map = dict(zip(self.tickers, self.weights))
            self.factor_exposure = calc_portfolio_factor_exposure(
                ticker_factors, weight_map, universe_factors
            )



