"""
Capture ratio calculations for stress testing.
"""

import pandas as pd
import numpy as np
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import PortfolioPerformanceCalculations
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics


def calculate_portfolio_capture_ratio(portfolio_returns: pd.Series, spy_returns: pd.Series):
    """
    Calculate portfolio upside/downside capture ratio against SPY.
    
    :param portfolio_returns: Portfolio returns series
    :param spy_returns: SPY benchmark returns series
    :return: Dictionary with capture metrics
    """
    if portfolio_returns.empty or spy_returns.empty:
        return "No portfolio or SPY data available"
    
    # Use the portfolio performance calculations method
    perf_calc = PortfolioPerformanceCalculations({}, '', '')  # Dummy initialization
    capture_metrics = perf_calc.calculate_upside_downside_capture(
        fund_returns=portfolio_returns,
        benchmark_returns=spy_returns
    )
    
    # Convert all numpy floats to Python floats
    for key, value in capture_metrics.items():
        if isinstance(value, (int, float)) and not np.isnan(value):
            capture_metrics[key] = float(round(value, 3))
    
    return capture_metrics


def calculate_ticker_capture_ratios(ticker_returns: pd.DataFrame, benchmark_ticker: str = 'SPY'):
    """
    Calculate individual ticker capture ratios for a stress scenario.
    
    :param ticker_returns: DataFrame of ticker returns
    :param benchmark_ticker: Ticker to use as benchmark (default: 'SPY')
    :return: Dictionary with capture metrics for each ticker
    """
    if ticker_returns.empty:
        return "No ticker data available"
    
    # Use the ticker performance calculations method
    ticker_capture_ratios = TickerPerformanceMetrics.calculate_ticker_capture_ratios(
        ticker_returns_df=ticker_returns,
        benchmark_ticker=benchmark_ticker
    )

    for ticker, capture_ratio in ticker_capture_ratios.items():
        if isinstance(capture_ratio, dict):
            for key, value in capture_ratio.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    ticker_capture_ratios[ticker][key] = float(round(value, 3))

    if 'SPY' in ticker_capture_ratios:
        del ticker_capture_ratios['SPY']

    return ticker_capture_ratios