"""Single-asset entity that computes risk and performance metrics from OHLCV data."""

import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_all import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_all import calc_all_performance_metrics
from app.core.calc_v2.models.risk import RiskMetrics
from app.core.calc_v2.models.performance import PerformanceMetrics
from app.core.calc_v2.technicals.calc_all import calc_all_technicals
from app.core.calc_v2.models.technicals import TickerTechnicals
from app.core.calc_v2.factors.calc_all import calc_all_factors
from app.core.calc_v2.models.factors import TickerFactors
from app.repositories.fundamentals.models import FundamentalsResult
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


class Ticker:
    """Single-asset entity that computes risk and performance metrics from OHLCV data."""

    def __init__(
        self,
        ticker: str,
        ohlcv_data: pd.DataFrame,
        benchmark_prices: pd.Series | None = None,
        fundamentals: FundamentalsResult | None = None,
    ):
        self.ticker = ticker
        self.ohlcv_data = ohlcv_data

        # Extract individual price series
        self.open = ohlcv_data['open']
        self.high = ohlcv_data['high']
        self.low = ohlcv_data['low']
        self.close = ohlcv_data['close']
        self.adj_close = ohlcv_data['adj_close']
        self.volume = ohlcv_data['volume']

        # Return series (computed from adj_close)
        self.daily_returns = self.adj_close.pct_change().dropna()
        self.cumulative_returns = (1 + self.daily_returns).cumprod() - 1
        self.log_returns = np.log(1 + self.daily_returns)
        self.cumulative_log_returns = np.log(1 + self.daily_returns).cumsum()

        # Benchmark
        self.benchmark_returns: pd.Series | None = None
        if benchmark_prices is not None:
            self.benchmark_returns = benchmark_prices.pct_change().dropna()

        # Metrics
        self.risk_metrics: RiskMetrics = calc_all_risk_metrics(
            self.daily_returns,
            self.benchmark_returns,
        )

        self.performance_metrics: PerformanceMetrics = calc_all_performance_metrics(
            self.daily_returns,
            self.benchmark_returns,
        )

        self.technicals: TickerTechnicals = calc_all_technicals(self.ohlcv_data)

        # Factor metrics
        self.factors: TickerFactors = calc_all_factors(
            adj_close=self.adj_close,
            daily_returns=self.daily_returns,
            benchmark_returns=self.benchmark_returns,
            fundamentals=fundamentals,
        )

if __name__ == '__main__':
    from app.repositories.fundamentals.fetchers import get_bulk_fundamentals

    tickers = ['AAL', 'SPY', 'NVDA', 'MSFT', 'TSLA', 'GOOGL', 'AMZN', 'META']

    import time
    start_time = time.time()
    data = fetch_bulk_ohlcv_data_for_tickers(tickers, '2024-01-01', '2026-01-31')
    fundamentals = get_bulk_fundamentals(tickers)
    end_time = time.time()
    print(f"Data fetch: {end_time - start_time:.2f}s")

    for ticker in tickers:
        start_time = time.time()
        ticker_obj = Ticker(
            ticker,
            data[ticker],
            data['SPY']['adj_close'],
            fundamentals=fundamentals.get(ticker),
        )
        end_time = time.time()
        print(f"\n{ticker} ({end_time - start_time:.2f}s)")
        print(f"  alpha={ticker_obj.performance_metrics.alpha}")
        print(f"  factors={ticker_obj.factors.momentum.r12_1}")
