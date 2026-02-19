"""Multi-asset portfolio entity that computes risk and performance metrics."""

import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_risk_metrics import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_performance_metrics import calc_all_performance_metrics
from app.core.calc_v2.models.risk_model import RiskMetrics
from app.core.calc_v2.models.performance_model import PerformanceMetrics
from app.core.calc_v2.models.correlation_model import CorrelationMetrics
from app.core.calc_v2.models.covariance_model import CovarianceMetrics
from app.core.calc_v2.portfolio_specific.group_metrics import (
    fetch_ticker_classifications,
    calc_group_metrics,
    calc_net_exposure,
    calc_gross_exposure,
    calc_long_exposure,
    calc_short_exposure,
)
from app.core.calc_v2.portfolio_specific.calc_correlation import (
    calc_correlation_matrix,
    calc_all_correlation_metrics,
    calc_rolling_avg_correlation,
)
from app.core.calc_v2.portfolio_specific.calc_covariance import calc_covariance_matrix, calc_all_covariance_metrics


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


if __name__ == '__main__':
    from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
    import time
    start_time = time.time()
    tickers = ['AAPL', 'MSFT', 'NVDA', 'PG', 'HYG']
    weights = [0.25, 0.25, 0.25, 0.2, 0.05]
    data = fetch_bulk_ohlcv_data_for_tickers(tickers + ['SPY'], '2020-01-01', '2026-01-31')
    price_df = pd.DataFrame({t: data[t]['adj_close'] for t in tickers})
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")

    start_time = time.time()
    portfolio = Portfolio('Test Portfolio', tickers, weights, price_df, data['SPY']['adj_close'])
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")


    print(portfolio.sector_metrics)
    print(portfolio.industry_metrics)
    print(portfolio.sub_industry_metrics)
