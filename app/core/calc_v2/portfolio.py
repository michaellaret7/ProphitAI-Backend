"""Multi-asset portfolio entity that computes risk and performance metrics."""

import random
import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_all import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_all import calc_all_performance_metrics
from app.core.calc_v2.models.risk import RiskMetrics
from app.core.calc_v2.models.performance import PerformanceMetrics
from app.core.calc_v2.models.correlation import CorrelationMetrics
from app.core.calc_v2.models.covariance import CovarianceMetrics
from app.core.calc_v2.models.group_metrics import GroupMetrics
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
from app.core.calc_v2.portfolio_analytics.factor_exposures import (
    calc_portfolio_factor_exposure,
    build_universe_factors,
)
from app.core.calc_v2.models.factors import PortfolioFactorExposure, TickerFactors
from app.core.calc_v2.models.stress_test import StressTestResult
from app.core.calc_v2.stress_test.calc_all import calc_all_stress_test


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
        etf_returns_map: dict[str, pd.Series] | None = None,
        shocks: dict[str, float] | None = None,
    ):
        if len(tickers) != len(weights):
            raise ValueError("Tickers must match the amount of weights")
        if len(tickers) != len(set(tickers)):
            dupes = [t for t in tickers if tickers.count(t) > 1]
            raise ValueError(f"Duplicate tickers not allowed — consolidate weights instead: {set(dupes)}")

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

        # Risk metrics (with optional benchmark for beta/tracking error)
        self.risk_metrics: RiskMetrics = calc_all_risk_metrics(
            self.daily_returns,
            self.benchmark_returns
        )

        self.performance_metrics: PerformanceMetrics = calc_all_performance_metrics(
            self.daily_returns,
            self.benchmark_returns
        )

        # ---- Cross-asset matrices (raw DataFrames + derived metrics) ----
        self.corr_matrix: pd.DataFrame = calc_correlation_matrix(self.asset_returns)
        self.cov_matrix: pd.DataFrame = calc_covariance_matrix(self.asset_returns)

        self.correlation_metrics: CorrelationMetrics = calc_all_correlation_metrics(self.asset_returns)
        self.covariance_metrics: CovarianceMetrics = calc_all_covariance_metrics(
            self.asset_returns, self.tickers, self.weights
        )

        # ---- Rolling average pairwise correlation (regime detection) ----
        self.rolling_avg_correlation: pd.Series = calc_rolling_avg_correlation(self.asset_returns)

        # Portfolio exposure metrics
        self.net_exposure: float = calc_net_exposure(self.weights)
        self.gross_exposure: float = calc_gross_exposure(self.weights)
        self.long_exposure: float = calc_long_exposure(self.weights)
        self.short_exposure: float = calc_short_exposure(self.weights)

        # Classification-based group metrics (VaR + concentration by sector/industry/sub_industry)
        classifications = fetch_ticker_classifications(self.tickers)

        self.sector_metrics: dict[str, GroupMetrics] = calc_group_metrics(
            'sector', classifications, self.tickers, self.weights, self.asset_returns
        )
        self.industry_metrics: dict[str, GroupMetrics] = calc_group_metrics(
            'industry', classifications, self.tickers, self.weights, self.asset_returns
        )
        self.sub_industry_metrics: dict[str, GroupMetrics] = calc_group_metrics(
            'sub_industry', classifications, self.tickers, self.weights, self.asset_returns
        )

        # Factor exposure (optional — requires ticker_factors + benchmark)
        self.factor_exposure: PortfolioFactorExposure | None = None

        if ticker_factors is not None and benchmark_prices is not None:
            import time
            universe_factors = build_universe_factors(benchmark_prices) # this is the portfolio construction bottleneck needs to be cached
            weight_map = dict(zip(self.tickers, self.weights))
            self.factor_exposure = calc_portfolio_factor_exposure(
                ticker_factors, weight_map, universe_factors
            )

        # Stress testing (optional — requires etf_returns_map + shocks)
        self.stress_test: StressTestResult | None = None

        if etf_returns_map is not None and shocks is not None:
            ticker_returns_map = {t: self.asset_returns[t] for t in self.tickers}
            weight_map = dict(zip(self.tickers, self.weights))
            self.stress_test = calc_all_stress_test(
                portfolio_returns=self.daily_returns,
                weights=weight_map,
                ticker_returns_map=ticker_returns_map,
                etf_returns_map=etf_returns_map,
                shocks=shocks,
            )


if __name__ == "__main__":
    from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers, fetch_bulk_price_data_for_tickers
    from app.core.calc_v2.ticker import Ticker
    import time

    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'JNJ', 'AAL', 'F']
    weights = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, -0.1, -0.1]

    # ETF shocks for stress testing
    shocks = {'SPY': -0.05, 'TLT': 0.10, 'GLD': -0.04, 'EEM': 0.15}

    start_time = time.time()
    ohlcv = fetch_bulk_ohlcv_data_for_tickers(tickers + ['SPY'], '2020-01-01', '2026-01-31')
    etf_prices = fetch_bulk_price_data_for_tickers(shocks.keys(), '2020-01-01', '2026-01-31')
    end_time = time.time()
    print(f"Data fetch: {end_time - start_time:.1f}s")

    benchmark = ohlcv['SPY']['adj_close']

    # Build ETF returns map (SPY from ohlcv + other ETFs from price fetch)
    etf_returns_map: dict[str, pd.Series] = {}
    etf_returns_map['SPY'] = benchmark.pct_change().dropna()
    for etf in shocks.keys():
        if etf in etf_prices.columns:
            etf_returns_map[etf] = etf_prices[etf].pct_change().dropna()

    t0 = time.time()
    ticker_factors = {t: Ticker(t, ohlcv[t], benchmark).factors for t in tickers}
    t1 = time.time()
    print(f"Ticker factors (17 Ticker objects): {t1 - t0:.1f}s")

    portfolio = Portfolio(
        name="Test Portfolio",
        tickers=tickers,
        weights=weights,
        price_df=pd.DataFrame({t: ohlcv[t]['adj_close'] for t in tickers}),
        benchmark_prices=benchmark,
        ticker_factors=ticker_factors,
        etf_returns_map=etf_returns_map,
        shocks=shocks,
    )
    t2 = time.time()
    print(f"Portfolio constructor: {t2 - t1:.1f}s")
    print(f"Total build: {t2 - t0:.1f}s")

    print(portfolio.performance_metrics)

