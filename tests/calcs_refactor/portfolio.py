import sys
from pathlib import Path

# Add project root and current directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uuid
import pandas as pd
import numpy as np
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.repositories.portfolio.retrieval import retrieve_portfolio
from calc_risk_metrics import calc_all_risk_metrics
from risk_model import RiskMetrics
from calc_performance_metrics import calc_all_performance_metrics
from performance_model import PerformanceMetrics

fetched_tickers = []
# Fetch portfolio positions and weights
portfolio_id = uuid.UUID("828f7921-8a3c-4c89-aa22-39888165e0df")
positions = retrieve_portfolio(portfolio_id=portfolio_id)

tickers = [p['ticker'] for p in positions]
weights = [p['allocation'] for p in positions]

fetched_tickers.extend(['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'CSCO', 'INTC', 'SPY', 'QQQ'])
fetched_tickers.extend(tickers)

# Fetch price data for portfolio tickers
price_df = fetch_bulk_ohlcv_data_for_tickers(fetched_tickers, '2012-01-01', '2026-01-31')
price_df = pd.DataFrame({
    ticker: df['adj_close'] for ticker, df in price_df.items()
}) 

benchmark_data = fetch_bulk_ohlcv_data_for_tickers(['SPY'], '2012-01-01', '2026-01-31')
benchmark_prices = benchmark_data['SPY']['adj_close']

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
    
import time 
start_time = time.time()
portfolio = Portfolio(
    name='User Portfolio',
    tickers=tickers,
    weights=weights,
    price_df=price_df,
    benchmark_prices=benchmark_prices
)
end_time = time.time()
print(f"Time taken to create portfolio: {end_time - start_time} seconds")

start_time = time.time()
portfolio_2 = Portfolio(
    name='User Portfolio 2',
    tickers=['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'CSCO', 'INTC', 'SPY', 'QQQ'],
    weights=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    price_df=price_df,
    benchmark_prices=benchmark_prices
)
end_time = time.time()
print(f"Time taken to create portfolio 2: {end_time - start_time} seconds")

print(portfolio_2.performance_metrics)
print(portfolio_2.risk_metrics)


