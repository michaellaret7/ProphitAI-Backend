"""Single-asset entity that computes risk and performance metrics from OHLCV data."""

import pandas as pd
import numpy as np

from app.core.calc_v2.risk.calc_risk_metrics import calc_all_risk_metrics
from app.core.calc_v2.performance.calc_performance_metrics import calc_all_performance_metrics
from app.core.calc_v2.models.risk_model import RiskMetrics
from app.core.calc_v2.models.performance_model import PerformanceMetrics

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


class Ticker:
    """Single-asset entity that computes risk and performance metrics from OHLCV data."""

    def __init__(
        self,
        ticker: str,
        ohlcv_data: pd.DataFrame,
        benchmark_prices: pd.Series | None = None,
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

