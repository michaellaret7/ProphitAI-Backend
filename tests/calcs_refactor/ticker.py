import sys
from pathlib import Path
# Add project root and current directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import numpy as np
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from calc_risk_metrics import calc_all_risk_metrics
from calc_performance_metrics import calc_all_performance_metrics

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

class Ticker:
    def __init__(
        self,
        ticker: str,
        ohclv_data: pd.DataFrame,
        benchmark_data: pd.DataFrame,
        benchmark_ticker: str = 'SPY'
    ):
        self.ticker = ticker
        self.ohclv_data = ohclv_data
        self.benchmark_data = benchmark_data

        self.daily_returns = self.ohclv_data[ticker]['adj_close'].pct_change().dropna()
        self.cumulative_returns = (1 + self.daily_returns).cumprod() - 1
        self.log_returns = np.log(1 + self.daily_returns)
        self.cumulative_log_returns = np.log(1 + self.daily_returns).cumsum()

        self.benchmark_returns = self.benchmark_data[benchmark_ticker]['adj_close'].pct_change().dropna()
        
        self.risk_metrics = calc_all_risk_metrics(
            self.daily_returns, 
            self.benchmark_returns
        )

        self.performance_metrics = calc_all_performance_metrics(
            self.daily_returns, 
            self.benchmark_returns
        )

