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


def get_liquidity_data():
    """
    Retrieve liquidity data for all available stock tickers.
    
    Returns:
        dict: Dictionary containing liquidity data for each ticker, JSON formatted.
    """
    return None 

def get_tickers() -> str:
    """Returns a list of available stock tickers."""
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
   # Database configuration
   if db_config is None:
      db_config = {
         "host": os.environ.get("DB_HOST"),
         "user": os.environ.get("DB_USER"),
         "password": os.environ.get("DB_PASSWORD"),
         "port": os.environ.get("DB_PORT")
      }
   
   # Normalize ticker
   ticker_upper = ticker.upper()
   ticker_lower = ticker.lower()
   
   # Load schema definition
   # Construct the path to database_schemas.json relative to this script's location
   script_dir = os.path.dirname(os.path.abspath(__file__))
   # Go up two directories (from tools to stress_test_agent, then to src)
   # then into data/database/
   schema_file_path = os.path.join(script_dir, '..', '..', 'data', 'database', 'database_schemas.json')
   # Normalize the path to resolve '..' and ensure it's in the correct format for the OS
   schema_file_path = os.path.normpath(schema_file_path)

   with open(schema_file_path, 'r') as f:
      schema_data = json.load(f)
   
   # Find ticker location
   ticker_location = None
   for sector_name, sector_info in schema_data.items():
      database = sector_info.get('database')
      schemas = sector_info.get('schemas', {})
      
      for schema_name, schema_info in schemas.items():
         tables = schema_info.get('tables', {})
         
         for table_name, table_info in tables.items():
            tickers = table_info.get('tickers', [])
            
            # Case-insensitive comparison
            for db_ticker in tickers:
               if ticker_upper.upper() == db_ticker.upper():
                  # Special case for ETFs - use specific database names
                  if "etf" in sector_name.lower():
                     db_name = "etf_prices"
                  else:
                     db_name = f"{database}_prices"
                     
                  ticker_location = {
                     "database": db_name,
                     "schema": f"{schema_name}_prices",
                     "ticker": db_ticker  # Use the ticker with the exact case from the database
                  }
                  break
         if ticker_location: break
      if ticker_location: break
   
   if not ticker_location:
      # Just pass silently if ticker not found
      return None
   
   try:
      # Connect to database
      db_config['dbname'] = ticker_location['database']
      conn = psycopg2.connect(**db_config)
      cursor = conn.cursor()
      
      # Query hourly data (taking the last 15-min bar of each hour)
      query = f"""
      WITH hourly_data AS (
         SELECT 
            date_trunc('hour', datetime) as hour_start,
            MAX(datetime) as last_bar_time
         FROM {ticker_location['schema']}.{ticker_lower}
         WHERE date BETWEEN %s AND %s
         GROUP BY date_trunc('hour', datetime)
      )
      SELECT 
         hd.hour_start as datetime,
         t.open,
         t.high,
         t.low,
         t.close,
         t.volume
      FROM hourly_data hd
      JOIN {ticker_location['schema']}.{ticker_lower} t
         ON t.datetime = hd.last_bar_time
      ORDER BY hd.hour_start
      """
      
      cursor.execute(query, (start_date_str, end_date_str))
      
      # Convert results
      results = []
      for row in cursor.fetchall():
         datetime_val, open_val, high_val, low_val, close_val, volume_val = row
         
         # Convert Decimal types to float
         if isinstance(open_val, Decimal):
            open_val = float(open_val)
         if isinstance(high_val, Decimal):
            high_val = float(high_val)
         if isinstance(low_val, Decimal):
            low_val = float(low_val)
         if isinstance(close_val, Decimal):
            close_val = float(close_val)
         if isinstance(volume_val, Decimal):
            volume_val = float(volume_val)
               
         results.append({
            "datetime": datetime_val,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": volume_val
         })

      # Create DataFrame and sort by datetime
      df = pd.DataFrame(results)
      if not df.empty:
         df = df.sort_values('datetime')
         
         # Convert to dictionary in the requested format
         data_dict = df.to_dict('records')
         return {ticker_upper: data_dict}
      else:
         return {ticker_upper: []}
      
   except Exception as e:
      # Just pass silently on error
      print(f"Error retrieving hourly data: {e}")
      return None
   
   finally:
      if 'conn' in locals() and conn:
         cursor.close()
         conn.close()

def calculate_stock_metrics(start_date_str: str, end_date_str: str):
    """
    Calculate various financial metrics for all available stock tickers for a given date range.
    
    Args:
        start_date_str (str): The start date in 'YYYY-MM-DD' format.
        end_date_str (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        dict: Dictionary containing calculated metrics for each ticker, JSON formatted.
    """
    all_metrics = {}
    
    # Define date range for analysis (previously hardcoded in get_stock_data)
    # start_date_str = "2023-03-06" # Removed hardcoded date
    # end_date_str = "2023-03-14"   # Removed hardcoded date

    # Get available tickers
    try:
        tickers_json = get_tickers()
        tickers = json.loads(tickers_json)
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return {}

    for ticker in tickers:
        # Get stock data
        stock_data = get_stock_data(ticker, start_date_str, end_date_str)
        
        if not stock_data or ticker not in stock_data or not stock_data[ticker]:
            print(f"Could not retrieve or process data for {ticker}")
            continue  # Skip to the next ticker if data is missing
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(stock_data[ticker])
        
        # Ensure datetime is properly sorted
        df = df.sort_values('datetime')
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Remove first row with NaN return
        df = df.dropna(subset=['returns'])
        
        # Skip if DataFrame is empty after dropping NaN
        if df.empty:
            print(f"Not enough data for {ticker} after processing.")
            continue

        # Calculate cumulative returns
        df['cum_returns'] = (1 + df['returns']).cumprod()
        
        # Calculate maximum drawdown
        df['peak'] = df['cum_returns'].cummax()
        df['drawdown'] = (df['cum_returns'] - df['peak']) / df['peak']
        max_drawdown = df['drawdown'].min()
        
        # Get peak and trough values
        peak_idx = df['cum_returns'].idxmax()
        peak_value = df.loc[peak_idx, 'close']
        peak_date = df.loc[peak_idx, 'datetime']
        
        # Find the minimum after the peak
        trough_idx = None
        trough_value = None
        trough_date = None
        
        if peak_idx < df.index[-1]:
            post_peak_df = df.loc[peak_idx:]
            trough_idx = post_peak_df['cum_returns'].idxmin()
            trough_value = df.loc[trough_idx, 'close']
            trough_date = df.loc[trough_idx, 'datetime']
        
        # Calculate peak to trough percentage
        peak_to_trough = None
        if peak_value is not None and trough_value is not None:
            peak_to_trough = (trough_value - peak_value) / peak_value
        
        # Calculate time to recover
        time_to_recover = None
        if trough_idx is not None:
            post_trough_df = df.loc[trough_idx:]
            # Find first point where value exceeds the peak again
            recovery_points = post_trough_df[post_trough_df['cum_returns'] >= df.loc[peak_idx, 'cum_returns']]
            
            if not recovery_points.empty:
                recovery_idx = recovery_points.index[0]
                recovery_date = df.loc[recovery_idx, 'datetime']
                time_to_recover = (recovery_date - trough_date).total_seconds() / 3600  # hours
        
        # Calculate annualized volatility
        # Standard deviation of returns * sqrt(252) for daily data or sqrt(252*24) for hourly data
        hourly_volatility = df['returns'].std()
        annualized_volatility = hourly_volatility * math.sqrt(252 * 24)  # Annualizing hourly data
        
        # Create results dictionary
        metrics = {
            'max_drawdown': max_drawdown * 100,  # Convert to percentage
            'annualized_volatility': annualized_volatility * 100,  # Convert to percentage
            'peak_value': peak_value,
            'peak_date': peak_date,
            'trough_value': trough_value,
            'trough_date': trough_date,
            'peak_to_trough': peak_to_trough * 100 if peak_to_trough is not None else None,  # Convert to percentage
            'time_to_recover_hours': time_to_recover
        }
        
        # Round numeric values to 4 decimal places
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                metrics[key] = round(value, 4)
            elif isinstance(value, datetime):
                 metrics[key] = value.isoformat() # Convert datetime to string for JSON compatibility

        all_metrics[ticker] = metrics

    return json.dumps(all_metrics)
