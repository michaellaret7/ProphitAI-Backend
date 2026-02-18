import sys
from pathlib import Path

# Add project root and current directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import numpy as np
from calc_risk_metrics import calc_all_risk_metrics
from risk_model import RiskMetrics
from calc_performance_metrics import calc_all_performance_metrics
from performance_model import PerformanceMetrics


class Portfolio:
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
    

if __name__ == '__main__':
    import json
    import matplotlib.pyplot as plt
    from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers

    tickers = ['PM', 'MO', 'KO', 'PG', 'PEP', 'HSY', 'CL', 'MDLZ']
    weights = [0.15, 0.15, 0.125, 0.125, 0.125, 0.125, 0.10, 0.10]

    # Fetch price data for portfolio tickers
    raw_data = fetch_bulk_ohlcv_data_for_tickers(tickers, '2020-01-01', '2026-01-31')
    price_df = pd.DataFrame({
        ticker: df['adj_close'] for ticker, df in raw_data.items()
    })

    benchmark_data = fetch_bulk_ohlcv_data_for_tickers(['XLP'], '2020-01-01', '2026-01-31')
    benchmark_prices = benchmark_data['XLP']['adj_close']

    portfolio = Portfolio(
        name="Portfolio",
        tickers=tickers,
        weights=weights,
        price_df=price_df,
        benchmark_prices=benchmark_prices,
    )

    print(json.dumps(portfolio.risk_metrics.model_dump(), indent=4))
    print(json.dumps(portfolio.performance_metrics.model_dump(), indent=4))

    benchmark_cumulative = (1 + portfolio.benchmark_returns).cumprod() - 1

    plt.plot(portfolio.cumulative_returns.index, portfolio.cumulative_returns * 100, label='Portfolio')
    plt.plot(benchmark_cumulative.index, benchmark_cumulative * 100, label='XLP Benchmark')
    plt.title('Cumulative Returns: Portfolio vs XLP')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()