"""Multi-asset portfolio entity that computes risk and performance metrics."""

import random
import pandas as pd
import numpy as np

from app.core.calculations.risk.calc_all import calc_all_risk_metrics
from app.core.calculations.performance.calc_all import calc_all_performance_metrics
from app.core.calculations.models.risk import RiskMetrics
from app.core.calculations.models.performance import PerformanceMetrics
from app.core.calculations.models.correlation import CorrelationMetrics
from app.core.calculations.models.covariance import CovarianceMetrics
from app.core.calculations.models.group_metrics import GroupMetrics
from app.core.calculations.portfolio_analytics.group_metrics import (
    fetch_ticker_classifications,
    calc_group_metrics,
    calc_net_exposure,
    calc_gross_exposure,
    calc_long_exposure,
    calc_short_exposure,
)
from app.core.calculations.portfolio_analytics.calc_correlation import (
    calc_correlation_matrix,
    calc_all_correlation_metrics,
    calc_rolling_avg_correlation,
)
from app.core.calculations.portfolio_analytics.calc_covariance import calc_covariance_matrix, calc_all_covariance_metrics
from app.core.calculations.portfolio_analytics.factor_exposures import (
    calc_portfolio_factor_exposure,
    get_universe_factors,
)
from app.core.calculations.models.factors import PortfolioFactorExposure, TickerFactors
from app.core.calculations.models.stress_test import StressTestResult
from app.core.calculations.stress_test.calc_all import calc_all_stress_test


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
        self.asset_returns = self.price_df.pct_change(fill_method=None).dropna()

        # Benchmark returns (calculated from prices)
        self.benchmark_returns: pd.Series | None = None

        if benchmark_prices is not None:
            self.benchmark_returns = benchmark_prices.pct_change(fill_method=None).dropna()

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
            universe_factors = get_universe_factors()
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
    from app.core.atlas.tools.portfolio.utils import build_portfolio_obj
    import time

    # tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'JNJ', 'AAL', 'F']
    # weights = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, -0.1, -0.1]
    tickers = ['TSLA', 'PLTR', 'ABBV', 'AMD', 'COST', 'NVDA']
    weights = [0.20, 0.20, 0.20, 0.20, 0.20, 0.20]
    shocks = {'SPY': -0.05, 'TLT': 0.10, 'GLD': -0.04, 'EEM': 0.15}

    t0 = time.time()
    portfolio = build_portfolio_obj(tickers, weights, years_back=2, shocks=shocks, with_factors=True)
    t1 = time.time()
    print(f"First build (cold cache): {t1 - t0:.1f}s")
    print('momentum:', portfolio.factor_exposure.momentum)
    print('value:', portfolio.factor_exposure.value)
    print('quality:', portfolio.factor_exposure.quality)
    print('growth:', portfolio.factor_exposure.growth)
    print('volatility:', portfolio.factor_exposure.volatility)
    print('size:', portfolio.factor_exposure.size)

    print(portfolio.stress_test)

