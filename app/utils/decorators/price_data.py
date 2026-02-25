"""Decorators for fetching price data.

Note: Dividend data fetching has been removed. Use adj_close for total returns
since it already accounts for dividends and splits.
"""

from functools import wraps
from datetime import timedelta

import yaml

from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.core.config import DEFAULT_LOOKBACK_1Y
from app.utils.time_utils import get_current_utc_time


def with_price_data(lookback_days=DEFAULT_LOOKBACK_1Y, include_dividends=True):
    """
    Decorator that fetches price data for a ticker before running the function.

    Note: include_dividends parameter is deprecated and ignored. Use adj_close
    from price data for total returns calculations.

    Usage:
        @with_price_data(lookback_days=252)
        def analyze_ticker(ticker, price_data=None):
            return calculate_something(price_data)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(ticker, *args, **kwargs):
            end = get_current_utc_time()
            start = end - timedelta(days=lookback_days)

            # Fetch price data directly from repository
            start_str = start.strftime('%Y-%m-%d')
            end_str = end.strftime('%Y-%m-%d')
            price_map = fetch_bulk_price_data_for_tickers([ticker], start_str, end_str)
            price_series = price_map[ticker] if ticker in price_map.columns else None

            if price_series is None or price_series.empty:
                return yaml.dump({"success": False, "error": f"No price data available for {ticker}"}, default_flow_style=False)

            kwargs['price_data'] = price_series

            # Dividend data no longer fetched - use adj_close for total returns
            # Reason: adj_close already accounts for dividends and splits
            kwargs['dividend_data'] = None

            return func(ticker, *args, **kwargs)

        return wrapper
    return decorator


def with_bulk_price_data(lookback_days=DEFAULT_LOOKBACK_1Y, include_dividends=True):
    """
    Decorator that fetches price data for a list of tickers before running the function.

    Note: include_dividends parameter is deprecated and ignored.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            end = get_current_utc_time()
            start = end - timedelta(days=lookback_days)

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

            # Fetch price data directly from repository
            start_str = start.strftime('%Y-%m-%d')
            end_str = end.strftime('%Y-%m-%d')
            price_series = fetch_bulk_price_data_for_tickers(tickers_list, start_str, end_str)

            kwargs['price_data'] = price_series

            return func(*args, **kwargs)

        return wrapper
    return decorator
