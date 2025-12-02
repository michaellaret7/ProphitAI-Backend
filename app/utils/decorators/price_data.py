"""Decorators for fetching price and dividend data."""

from functools import wraps
from datetime import datetime, timedelta, timezone
from app.core.calculations.core.data_service import DataService
from app.core.calculations.core.config import DEFAULT_LOOKBACK_1Y
import yaml

def with_price_data(lookback_days=DEFAULT_LOOKBACK_1Y, include_dividends=True):
    """
    Decorator that fetches price and dividend data for a ticker before running the function.

    Usage:
        @with_price_data(lookback_days=252, include_dividends=True)
        def analyze_ticker(ticker, price_data=None, dividend_data=None, _simulation_date=None):
            # price_data and dividend_data are automatically fetched
            return calculate_something(price_data)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(ticker, *args, **kwargs):
            # Get date range - use simulation date if provided
            # Reason: Simulation mode requires fetching historical data up to cutoff date
            simulation_date = kwargs.get('_simulation_date')
            end = simulation_date if simulation_date else datetime.now(timezone.utc)
            start = end - timedelta(days=lookback_days)

            # Fetch price data
            ds = DataService()
            price_series = ds.get_bulk_close_series([ticker], start, end).get(ticker)

            if price_series is None or price_series.empty:
                return yaml.dump({"success": False, "error": f"No price data available for {ticker}"}, default_flow_style=False)

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

def with_bulk_price_data(lookback_days=DEFAULT_LOOKBACK_1Y, include_dividends=True):
    """
    Decorator that fetches price and dividend data for a list of tickers before running the function.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get date range - use simulation date if provided
            # Reason: Simulation mode requires fetching historical data up to cutoff date
            simulation_date = kwargs.get('_simulation_date')
            end = simulation_date if simulation_date else datetime.now(timezone.utc)
            start = end - timedelta(days=lookback_days)

            # Fetch price data
            ds = DataService()
            # Support either 'ticker' (single) or 'tickers' (list/iterable) inputs
            tickers_param = None
            if 'tickers' in kwargs and kwargs['tickers']:
                tickers_param = kwargs['tickers']
            elif 'ticker' in kwargs and kwargs['ticker']:
                tickers_param = [kwargs['ticker']]
            elif len(args) > 0:
                tickers_param = args[0]
            else:
                return yaml.dump({"success": False, "error": "No ticker(s) provided to decorated function"}, default_flow_style=False)

            if isinstance(tickers_param, str):
                tickers_list = [tickers_param]
            else:
                try:
                    tickers_list = list(tickers_param)
                except Exception:
                    tickers_list = [str(tickers_param)]

            price_series = ds.get_bulk_close_series(tickers_list, start, end)

            kwargs['price_data'] = price_series

            # Avoid injecting dividend_data here to prevent unexpected kwargs
            # The wrapped function can fetch dividends as needed.
            return func(*args, **kwargs)

        return wrapper
    return decorator