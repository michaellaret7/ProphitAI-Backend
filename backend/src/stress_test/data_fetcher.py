"""
Data fetching utilities for stress testing.
"""

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from backend.src.repositories.price_data import get_price_data_15_mins, get_price_data_daily


def fetch_15min_data(ticker: str, start_date: str, end_date: str):
    """
    Helper function to fetch 15-minute data for a single ticker.
    
    :param ticker: Stock ticker symbol
    :param start_date: Start date in 'YYYY-MM-DD' format
    :param end_date: End date in 'YYYY-MM-DD' format
    :return: tuple (ticker, price_series) or (ticker, None) if error
    """
    ticker_upper = ticker.upper()
    
    price_data = get_price_data_15_mins(
        ticker=ticker_upper,
        start_date=datetime.strptime(start_date, '%Y-%m-%d'),
        end_date=datetime.strptime(end_date, '%Y-%m-%d')
    )
    
    if price_data is not None and not price_data.empty and 'close' in price_data.columns:
        return ticker, price_data['close']
    
    return ticker, None

def fetch_daily_data(ticker: str, start_date: str, end_date: str):
    """
    Helper function to fetch daily data for a single ticker.
    """
    ticker_upper = ticker.upper()
    price_data = get_price_data_daily(ticker_upper, start_date, end_date)

    if price_data is not None and not price_data.empty and 'close' in price_data.columns:
        return ticker, price_data['close']
    
    return ticker, None

def calculate_price_returns(portfolio: dict, start_date: str, end_date: str):
    """
    Calculates the 15-minute interval price returns for the portfolio and individual tickers.
    Uses thread pooling to fetch 15-minute data efficiently.
    
    :param portfolio: Dictionary of ticker symbols and weights
    :param start_date: Start date for the analysis in 'YYYY-MM-DD' format
    :param end_date: End date for the analysis in 'YYYY-MM-DD' format
    :return: tuple (portfolio_returns: pd.Series, ticker_returns: pd.DataFrame)
    """
    # Include SPY as benchmark along with portfolio tickers
    tickers_to_fetch = list(portfolio.keys()) + ['SPY']
    
    # Fetch all ticker data using thread pool
    all_prices_series = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(fetch_15min_data, ticker, start_date, end_date): ticker
            for ticker in tickers_to_fetch
        }
        
        for future in as_completed(future_to_ticker):
            try:
                ticker, close_series = future.result()
                if close_series is not None:
                    close_series.name = ticker.upper()
                    all_prices_series.append(close_series)
            except Exception as e:
                ticker = future_to_ticker[future]
                print(f"Error fetching 15-minute data for {ticker}: {e}")
    
    if not all_prices_series:
        return pd.Series(dtype=float), pd.DataFrame()
    
    # Combine all price series into a DataFrame
    close_prices_df = pd.concat(all_prices_series, axis=1)
    
    # Calculate returns for each ticker (including SPY)
    ticker_returns = close_prices_df.pct_change()
    
    # Apply portfolio weights (only to portfolio tickers, not SPY)
    portfolio_ticker_returns = ticker_returns[[col for col in ticker_returns.columns if col in [k.upper() for k in portfolio.keys()]]]
    weights = pd.Series({k.upper(): v for k, v in portfolio.items()})
    portfolio_returns = (portfolio_ticker_returns * weights).sum(axis=1)
    
    # Remove the first NaN value from pct_change
    portfolio_returns = portfolio_returns.iloc[1:]
    ticker_returns = ticker_returns.iloc[1:]
    
    return portfolio_returns, ticker_returns