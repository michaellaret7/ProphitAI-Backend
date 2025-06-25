import json
import openai
import os
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
import numpy as np
import math
from functools import lru_cache
from backend.src.utils.database import get_default_db_config
from backend.src.utils.financial_calculations import calculate_max_drawdown, calculate_volatility
from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository


def get_liquidity_data():
    """
    Retrieve liquidity data for all available stock tickers.
    
    Returns:
        dict: Dictionary containing liquidity data for each ticker, JSON formatted.
    """
    return None 

def get_tickers() -> str:
    """
    Get a list of available stock ticker symbols.
    
    Returns:
        str: JSON formatted list of ticker symbols
    """
    tickers = ["NVDA", "AMD", "AAL", "F", "TSLA", "MSFT", "AAPL", "AMZN", "INTC", "IBM", "NFLX", "PYPL", "UBER"]
    return json.dumps(tickers)

def get_portfolio_returns(start_date_str: str, end_date_str: str):
    """
    Calculate the cumulative hourly returns for an equally weighted portfolio of all available tickers.

    Args:
        start_date_str (str): The start date in 'YYYY-MM-DD' format.
        end_date_str (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        str: JSON formatted string containing a timeseries of cumulative portfolio returns.
             Example: {"2023-03-08T10:00:00": 0.0, "2023-03-08T11:00:00": 0.5, ...}
    """
    all_ticker_data = {}

    # Get available tickers
    try:
        tickers_json = get_tickers()
        tickers = json.loads(tickers_json)
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return json.dumps({"error": "Failed to retrieve tickers"})

    # Fetch data for all tickers
    for ticker in tickers:
        stock_data_dict = get_stock_data(ticker, start_date_str, end_date_str)
        if stock_data_dict and ticker in stock_data_dict and stock_data_dict[ticker]:
            df = pd.DataFrame(stock_data_dict[ticker])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            # Keep only the close price for merging
            all_ticker_data[ticker] = df[['close']]
        else:
            print(f"Warning: Could not retrieve sufficient data for {ticker} between {start_date_str} and {end_date_str}. Excluding from portfolio calculation.")

    if not all_ticker_data:
        return json.dumps({"error": "No data found for any ticker in the specified range."}) 

    # Combine all ticker close prices into one DataFrame
    # Use outer join to keep all timestamps, align data
    portfolio_df = pd.concat(all_ticker_data.values(), axis=1, keys=all_ticker_data.keys(), join='outer')
    portfolio_df.columns = portfolio_df.columns.droplevel(1) # Drop the 'close' level from MultiIndex

    # Forward fill missing values - assumes price stays constant if missing for an hour
    portfolio_df = portfolio_df.ffill()
    # Drop any remaining NaNs (e.g., at the beginning if ffill didn't cover)
    portfolio_df = portfolio_df.dropna()
    
    if portfolio_df.empty:
        return json.dumps({"error": "Insufficient overlapping data to calculate portfolio returns."}) 

    # Calculate hourly returns for each stock
    hourly_returns = portfolio_df.pct_change()

    # Calculate the mean return across all stocks for each hour (equal weighting)
    portfolio_hourly_returns = hourly_returns.mean(axis=1)

    # Calculate cumulative portfolio return
    # (1 + R1) * (1 + R2) * ... - 1
    cumulative_returns = (1 + portfolio_hourly_returns).cumprod() - 1
    
    # Convert to percentage and handle potential NaNs/Infs
    cumulative_returns_pct = (cumulative_returns * 100).replace([np.inf, -np.inf], None).fillna(0)

    # Format for JSON output
    results_dict = cumulative_returns_pct.round(2).to_dict() # Round to 2 decimal places
    # Convert Timestamp keys to strings and format value as percentage string
    results_json_compatible = {dt.isoformat(): f"{value}%" for dt, value in results_dict.items()}

    return json.dumps(results_json_compatible)

def get_stock_data(ticker: str, start_date_str: str, end_date_str: str, db_config=None):
    """
    Retrieve stock data in one-hour increments for a given ticker between specified dates.
    The data is stored in 15-minute bars in the database.
    
    Args:
        ticker (str): The stock ticker symbol
        start_date_str (str): The start date in 'YYYY-MM-DD' format.
        end_date_str (str): The end date in 'YYYY-MM-DD' format.
        db_config (dict, optional): Database configuration parameters
        
    Returns:
        dict: Dictionary with format {'ticker': {data}} or None if not found
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    # Ensure end_date includes the entire day
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    # years = (end_date - start_date).days / 365.0 # No longer needed
    
    # Get hourly data using the generic function, providing explicit start and end dates
    result = EquityPriceDataRepository().fetch_equity_price_data(ticker, start_date=start_date, end_date=end_date, interval='1H')
    
    if result is None:
        return None
    
    # Filter the results to only include data within the specified date range
    if isinstance(result, dict) and ticker.upper() in result:
        filtered_data = []
        for data_point in result[ticker.upper()]:
            if isinstance(data_point['datetime'], datetime):
                data_datetime = data_point['datetime']
            else:
                data_datetime = datetime.fromisoformat(str(data_point['datetime']))
            
            # Check if the data point is within the requested date range
            if start_date <= data_datetime <= end_date:
                filtered_data.append(data_point)
        
        return {ticker.upper(): filtered_data}
    
    return result

def calculate_stock_metrics(start_date_str: str, end_date_str: str):
    """
    Calculate various financial metrics for all available stock tickers for a given date range.
    
    Args:
        start_date_str: The start date in 'YYYY-MM-DD' format
        end_date_str: The end date in 'YYYY-MM-DD' format

    Returns:
        str: JSON formatted dictionary containing calculated metrics for each ticker
    """
    all_metrics = {}
    
    try:
        tickers_json = get_tickers()
        tickers = json.loads(tickers_json)
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return {}

    for ticker in tickers:
        stock_data = get_stock_data(ticker, start_date_str, end_date_str)
        
        if not stock_data or ticker not in stock_data or not stock_data[ticker]:
            print(f"Could not retrieve or process data for {ticker}")
            continue
        
        df = pd.DataFrame(stock_data[ticker])
        if df.empty:
            print(f"No data for {ticker} in the specified range.")
            continue
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        df['returns'] = df['close'].pct_change()
        df = df.dropna(subset=['returns'])
        
        if df.empty:
            print(f"Not enough data for {ticker} after processing returns.")
            continue

        df['cum_returns'] = (1 + df['returns']).cumprod()
        
        # Use utility functions for calculations
        max_dd = calculate_max_drawdown(df['cum_returns']) 
        # For annualized_volatility, we need to know the trading periods per year for hourly data
        # get_annualization_factor from utils can be used if bar_size is known, 
        # but get_stock_data returns 1-hour increments, so let's assume 252*6.5 for a 6.5 hour trading day.
        # Or more simply, use the existing math.sqrt(252*24) for hourly data if that's the desired convention.
        periods_per_year = 252 * 24 # Assuming 24 hours for simplicity, adjust if trading hours are specific
        annualized_vol = calculate_volatility(df['returns'], annualize=True, trading_days=periods_per_year) 
        
        peak_idx = df['cum_returns'].idxmax()
        peak_value = df.loc[peak_idx, 'close']
        peak_date = df.loc[peak_idx, 'datetime']
        
        trough_idx = None
        trough_value = None
        trough_date = None
        peak_to_trough = None
        time_to_recover = None
        
        if not df[df['cum_returns'] < df.loc[peak_idx, 'cum_returns']].empty:
            # Find the minimum cumulative return after the peak
            post_peak_df = df.loc[peak_idx:]
            if not post_peak_df.empty:
                trough_idx = post_peak_df['cum_returns'].idxmin()
                trough_value = df.loc[trough_idx, 'close']
                trough_date = df.loc[trough_idx, 'datetime']
                if peak_value is not None and trough_value is not None:
                     peak_to_trough = (trough_value - peak_value) / peak_value if peak_value != 0 else 0

                # Calculate time to recover
                if trough_idx is not None:
                    post_trough_df = df.loc[trough_idx:]
                    recovery_points = post_trough_df[post_trough_df['cum_returns'] >= df.loc[peak_idx, 'cum_returns']]
                    if not recovery_points.empty:
                        recovery_idx = recovery_points.index[0]
                        recovery_date = df.loc[recovery_idx, 'datetime']
                        time_to_recover = (recovery_date - trough_date).total_seconds() / 3600  # hours
        
        metrics = {
            'max_drawdown': max_dd * 100,  # Already a percentage from calculate_max_drawdown
            'annualized_volatility': annualized_vol * 100, # Already a percentage from calculate_volatility
            'peak_value': peak_value,
            'peak_date': peak_date.isoformat() if pd.notnull(peak_date) else None,
            'trough_value': trough_value,
            'trough_date': trough_date.isoformat() if pd.notnull(trough_date) else None,
            'peak_to_trough': peak_to_trough * 100 if peak_to_trough is not None else None,
            'time_to_recover_hours': time_to_recover
        }
        
        # Round numeric values to 4 decimal places
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                metrics[key] = round(value, 4)

        all_metrics[ticker] = metrics

    return json.dumps(all_metrics)
