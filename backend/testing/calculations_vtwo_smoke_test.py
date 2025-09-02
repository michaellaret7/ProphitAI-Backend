"""
Simple test to calculate Sharpe ratio for a portfolio using calculations_v2
"""

from datetime import datetime
import pandas as pd

# Import necessary components from calculations_v2
from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.returns.calculator import PortfolioReturnsCalculator
from backend.src.calculations_v2.performance.calculator import PerformanceCalculator


def calculate_portfolio_sharpe_ratio():
    """
    Calculate Sharpe ratio for a simple portfolio.
    """
    # Define portfolio
    portfolio_weights = {
        'AAPL': -0.4,
        'MSFT': -0.3,
        'GOOGL': -0.3,
        'SPY': 0.2,
        'QQQ': 0.2,
        'IWM': 0.2,
    }
    
    # Set date range
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 1, 1)
    
    # Initialize data service
    data_service = DataService()
    
    # Fetch price data for each ticker
    ticker_closes = {}
    for ticker in portfolio_weights.keys():
        try:
            price_data = data_service.get_price_data(ticker, start_date, end_date)
            ticker_closes[ticker] = price_data.frame['close']
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None
    
    # Calculate portfolio daily returns (using price returns for simplicity)
    ticker_returns = {}
    for ticker, close_series in ticker_closes.items():
        ticker_returns[ticker] = close_series.pct_change().dropna()
    
    # Get weighted portfolio returns
    portfolio_daily_returns = PortfolioReturnsCalculator.weighted_daily_returns(
        ticker_returns, 
        portfolio_weights
    )
    
    # Calculate Sharpe ratio
    sharpe_ratio = PerformanceCalculator.sharpe_ratio(portfolio_daily_returns)
    
    # Display results
    print(f"Portfolio Composition:")
    for ticker, weight in portfolio_weights.items():
        print(f"  {ticker}: {weight:.1%}")
    print(f"\nDate Range: {start_date.date()} to {end_date.date()}")
    print(f"Number of trading days: {len(portfolio_daily_returns)}")
    print(f"Portfolio Sharpe Ratio: {sharpe_ratio:.4f}")
    
    return sharpe_ratio


if __name__ == "__main__":
    calculate_portfolio_sharpe_ratio()
