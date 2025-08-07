"""
Capture ratio calculations for stress testing.
"""
import json
import pandas as pd
import numpy as np
from backend.src.repositories.price_data import get_price_data_daily, get_price_data_15_mins
from datetime import datetime, timedelta
from backend.src.stress_test.historical_shocks.scenarios import STRESS_SCENARIOS

def calculate_capture_ratios(ticker, benchmark='SPY', start_date=None, end_date=None, frequency='daily'):
    """
    Calculate upside and downside capture ratios for a ticker against a benchmark.
    
    Parameters:
    -----------
    ticker : str
        The ticker symbol to analyze (e.g., 'AAPL', 'MSFT')
    benchmark : str
        The benchmark ticker symbol (default: 'SPY' for S&P 500)
    start_date : datetime
        Start date for analysis (default: 5 years ago)
    end_date : datetime
        End date for analysis (default: today)
    
    Returns:
    --------
    dict : Dictionary containing capture ratios and detailed results
    """
    
    # Set default dates if not provided
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=252)  # 5 years default
    
    # Get price data for ticker
    if frequency == 'daily':
        ticker_data = get_price_data_daily(ticker, start_date, end_date)
        benchmark_data = get_price_data_daily(benchmark, start_date, end_date)
    elif frequency == '15mins':
        ticker_data = get_price_data_15_mins(ticker, start_date, end_date)
        benchmark_data = get_price_data_15_mins(benchmark, start_date, end_date)
    
    # Check if data is available
    if ticker_data.empty or benchmark_data.empty:
        print(f"No data available for {ticker} or {benchmark} in the specified date range")
        return None
    
    # The data fetching functions return DataFrames with a datetime index.
    # We can directly concatenate them, and pandas will align them by date.
    combined_data = pd.concat([ticker_data['close'], benchmark_data['close']], axis=1, keys=[ticker, benchmark]).dropna()
    
    # Calculate returns
    returns = combined_data.pct_change().dropna()
    
    # Calculate upside capture ratio
    up_market = returns[returns[benchmark] > 0]
    if len(up_market) > 0:
        # Use average returns for capture ratios
        up_ticker_avg = up_market[ticker].mean()
        up_benchmark_avg = up_market[benchmark].mean()
        upside_capture = (up_ticker_avg / up_benchmark_avg) 
    else:
        upside_capture = np.nan
    
    # Calculate downside capture ratio
    down_market = returns[returns[benchmark] < 0]
    if len(down_market) > 0:
        # Use average returns for capture ratios
        down_ticker_avg = down_market[ticker].mean()
        down_benchmark_avg = down_market[benchmark].mean()
        downside_capture = (down_ticker_avg / down_benchmark_avg) 
    else:
        downside_capture = np.nan
    
    # Calculate capture ratio (upside/downside)
    if pd.notna(downside_capture) and downside_capture != 0:
        capture_ratio = upside_capture / downside_capture
    else:
        capture_ratio = np.nan
    
    results = {
        'upside_capture': round(float(upside_capture), 4),
        'downside_capture': round(float(downside_capture), 4),
        'capture_ratio': round(float(capture_ratio), 4)
    }
    
    return results


if __name__ == "__main__":
    portfolio_dict = {
        # Long positions
        "CASY": {"conviction": 0.10, "position": "long"},
        "CELH": {"conviction": 0.10, "position": "long"},
        "ODC": {"conviction": 0.05, "position": "long"},
        "ODD": {"conviction": 0.05, "position": "long"},
        "PM": {"conviction": 0.05, "position": "long"},
        "VITL": {"conviction": 0.05, "position": "long"},
        "WMT": {"conviction": 0.05, "position": "long"},
        "BJ": {"conviction": 0.05, "position": "long"},
        "SFM": {"conviction": 0.05, "position": "long"},
        "COCO": {"conviction": 0.05, "position": "long"},
        "MNST": {"conviction": 0.05, "position": "long"},
        "CL": {"conviction": 0.05, "position": "long"},
        "IPAR": {"conviction": 0.05, "position": "long"},
        "TPB": {"conviction": 0.05, "position": "long"},
        "DOLE": {"conviction": 0.05, "position": "long"},
        "PPC": {"conviction": 0.05, "position": "long"},
        "INGR": {"conviction": 0.05, "position": "long"},
        # Short positions
        "WBA": {"conviction": 0.05, "position": "short"},
        "ANDE": {"conviction": 0.05, "position": "short"},
        "TGT": {"conviction": 0.02, "position": "short"},
        "STZ": {"conviction": 0.05, "position": "short"},
        "PEP": {"conviction": 0.05, "position": "short"},
        "SAM": {"conviction": 0.05, "position": "short"},
        "MGPI": {"conviction": 0.05, "position": "short"},
        "ENR": {"conviction": 0.05, "position": "short"},
        "SPB": {"conviction": 0.05, "position": "short"},
        "COTY": {"conviction": 0.05, "position": "short"},
        "KVUE": {"conviction": 0.05, "position": "short"},
        "KLG": {"conviction": 0.05, "position": "short"},
        "JJSF": {"conviction": 0.05, "position": "short"},
        "SEB": {"conviction": 0.05, "position": "short"}
    }

    for ticker in portfolio_dict.keys():
        results = calculate_capture_ratios(ticker, 'SPY')
        print(results)