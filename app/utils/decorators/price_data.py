"""Decorators for fetching price and dividend data."""

from functools import wraps
from datetime import datetime, timedelta, timezone
from app.core.calculations.core.data_service import DataService

def with_price_data(lookback_days=252, include_dividends=True):
    """
    Decorator that fetches price and dividend data for a ticker before running the function.
    
    Usage:
        @with_price_data(lookback_days=252, include_dividends=True)
        def analyze_ticker(ticker, price_data=None, dividend_data=None):
            # price_data and dividend_data are automatically fetched
            return calculate_something(price_data)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(ticker, *args, **kwargs):
            # Get date range
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=lookback_days)
            
            # Fetch price data
            ds = DataService()
            price_series = ds.get_bulk_close_series([ticker], start, end).get(ticker)
            
            if price_series is None or price_series.empty:
                return {"error": f"No price data available for {ticker}"}
            
            kwargs['price_data'] = price_series
            
            # Get dividend data if requested
            if include_dividends:
                try:
                    div_data = ds.get_dividends(ticker, start, end)
                    kwargs['dividend_data'] = div_data.series
                except:
                    kwargs['dividend_data'] = None
            
            return func(ticker, *args, **kwargs)
        
        return wrapper
    return decorator

def with_bulk_price_data(lookback_days=252, include_dividends=True):
    """
    Decorator that fetches price and dividend data for a list of tickers before running the function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(tickers, *args, **kwargs):
            # Get date range
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=lookback_days)
            
            # Fetch price data
            ds = DataService()
            price_series = ds.get_bulk_close_series(tickers, start, end)
            
            kwargs['price_data'] = price_series
            
            # Get dividend data if requested
            if include_dividends:
                try:
                    div_data = ds.get_dividends(tickers, start, end)
                    kwargs['dividend_data'] = div_data.series
                except:
                    kwargs['dividend_data'] = None
            
            return func(tickers, *args, **kwargs)
        
        return wrapper
    return decorator