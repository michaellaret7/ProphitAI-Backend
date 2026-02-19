"""Multi-asset portfolio entity that computes risk and performance metrics."""

import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_all import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_all import calc_all_performance_metrics
from app.core.calc_v2.models.risk_model import RiskMetrics
from app.core.calc_v2.models.performance_model import PerformanceMetrics
from app.core.calc_v2.models.correlation_model import CorrelationMetrics
from app.core.calc_v2.models.covariance_model import CovarianceMetrics
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

    tickers = [
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK-B', 'JPM', 'V',
        'UNH', 'XOM', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
        'KO', 'PEP', 'COST', 'AVGO', 'LLY', 'TMO', 'MCD', 'CSCO', 'ACN', 'ABT',
        'DHR', 'NEE', 'TXN', 'PM', 'UPS', 'MS', 'RTX', 'HON', 'UNP', 'LOW',
        'INTC', 'QCOM', 'AMGN', 'IBM', 'CAT', 'GE', 'BA', 'SBUX', 'GS', 'BLK',
        'MDLZ', 'ADI', 'GILD', 'SYK', 'MMC', 'CB', 'ADP', 'CI', 'DE', 'SO',
        'DUK', 'CL', 'CME', 'MO', 'ZTS', 'TGT', 'BDX', 'PLD', 'APD', 'SHW',
        'FIS', 'ITW', 'EMR', 'NSC', 'ETN', 'AON', 'WM', 'ECL', 'HUM', 'ORLY',
        'MCK', 'GM', 'F', 'PSA', 'KMB', 'AEP', 'D', 'SRE', 'AFL', 'TRV',
        'ALL', 'PRU', 'AIG', 'MET', 'PNC', 'USB', 'SCHW', 'COF', 'FDX', 'HYG',
    ]
    weights = [0.01] * 100

    print(f"Testing with {len(tickers)} tickers...")

    start_time = time.time()
    data = fetch_bulk_ohlcv_data_for_tickers(tickers + ['SPY'], '2020-01-01', '2026-01-31')
    fetch_time = time.time() - start_time
    print(f"Data fetch: {fetch_time:.2f}s")

    # Reason: Some tickers may not have data — filter to those that do.
    available = [t for t in tickers if t in data]
    weights = [0.01] * len(available)
    print(f"Available tickers: {len(available)} / {len(tickers)}")

    price_df = pd.DataFrame({t: data[t]['adj_close'] for t in available})

    start_time = time.time()
    portfolio = Portfolio('100-Ticker Test', available, weights, price_df, data['SPY']['adj_close'])
    portfolio_time = time.time() - start_time
    print(f"Portfolio construction: {portfolio_time:.2f}s")

    print(f"\nNet exposure: {portfolio.net_exposure:.4f}")
    print(f"Gross exposure: {portfolio.gross_exposure:.4f}")
    print(f"Sharpe: {portfolio.performance_metrics.sharpe_ratio}")
    print(f"Max drawdown: {portfolio.risk_metrics.max_drawdown}")
    print(f"Rolling avg corr length: {portfolio.rolling_avg_correlation}")
    print(f"Sectors: {list(portfolio.sector_metrics.keys())}")
