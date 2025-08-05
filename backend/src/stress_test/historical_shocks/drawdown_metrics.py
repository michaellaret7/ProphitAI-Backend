"""
Drawdown analysis for stress testing.
"""

import pandas as pd
import numpy as np

def calculate_portfolio_max_drawdown(portfolio_returns: pd.Series):
    """
    Calculate maximum drawdown for portfolio.
    
    :param portfolio_returns: Portfolio returns series
    :return: Float representing the maximum drawdown
    """
    min_return = portfolio_returns.min()
    return float(round(min_return, 3)) if not np.isnan(min_return) else min_return


def calculate_ticker_max_drawdowns(ticker_returns: pd.DataFrame, num_tickers: int = 5):
    """
    Calculate maximum drawdown for individual tickers.
    
    :param ticker_returns: DataFrame of ticker returns
    :param num_tickers: Number of tickers to return (default: 5)
    :return: Dict of ticker drawdowns sorted by worst drawdown
    """
    if ticker_returns.empty:
        return "No ticker data available"
    
    ticker_drawdowns = {}
    
    for ticker in ticker_returns.columns:
        if ticker != 'SPY':  # Exclude SPY from analysis
            returns = ticker_returns[ticker].dropna()
            if not returns.empty:
                cumulative = (1 + returns).cumprod()
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min()  # Most negative value
                ticker_drawdowns[ticker] = float(round(max_drawdown, 4)) if not np.isnan(max_drawdown) else max_drawdown
    
    # Sort by worst drawdown (most negative) and get top N
    top_n = sorted(ticker_drawdowns.items(), key=lambda x: x[1])[:num_tickers]
    
    # Convert to dictionary format
    return dict(top_n)