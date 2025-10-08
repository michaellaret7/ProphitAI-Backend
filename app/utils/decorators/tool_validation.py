"""Reusable validation decorators for agent tools.

This module provides decorators to validate tool arguments before execution,
ensuring clean error messages are returned to agents instead of confusing
data fetch errors.
"""

import yaml
import pandas as pd
from datetime import datetime
from functools import wraps
from typing import Callable, Any, List, Optional
import inspect

# ============================================================================
# SHARED HELPER FUNCTIONS
# ============================================================================

def _get_arg_value(arg_name: str, args: tuple, kwargs: dict, func: Callable) -> Any:
    """Extract argument value from args or kwargs.

    Args:
        arg_name: Name of the argument to extract
        args: Positional arguments passed to function
        kwargs: Keyword arguments passed to function
        func: The decorated function

    Returns:
        The argument value, or None if not found
    """
    # First check kwargs (most common case)
    value = kwargs.get(arg_name)

    # If not in kwargs, try to extract from positional args
    if value is None and args:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        if arg_name in params:
            idx = params.index(arg_name)
            if idx < len(args):
                value = args[idx]

    return value


def _build_yaml_error(error_message: str) -> str:
    """Build standardized YAML error response.

    Args:
        error_message: The error message to return

    Returns:
        YAML-formatted error string
    """
    return yaml.dump({
        "success": False,
        "error": error_message
    }, default_flow_style=False)


def validate_ticker_arg(arg_name: str = "ticker") -> Callable:
    """Decorator to validate a single ticker argument.

    Args:
        arg_name: Name of the ticker parameter to validate (default: "ticker")

    Returns:
        Decorator that validates ticker format before calling the function

    Example:
        @validate_ticker_arg()
        def get_ticker_data(ticker: str) -> str:
            # ticker is guaranteed to be valid string format
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            ticker = _get_arg_value(arg_name, args, kwargs, func)

            if ticker is None:
                return _build_yaml_error(
                    f"Missing required argument: '{arg_name}'. Example: {arg_name}='AAPL'"
                )

            if ticker is not None:
                if not isinstance(ticker, str):
                    return _build_yaml_error(
                        f"Invalid {arg_name} type: expected string, got {type(ticker).__name__}. Example: {arg_name}='AAPL'"
                    )

                ticker_clean = ticker.strip().upper()

                if not ticker_clean:
                    return _build_yaml_error(f"Empty {arg_name} string provided. Example: {arg_name}='AAPL'")

                if ticker_clean.startswith('[') or ticker_clean.startswith('{'):
                    return _build_yaml_error(
                        f"Invalid {arg_name} format: appears to be a list or dict ('{ticker_clean}'). Pass a single ticker string. Example: {arg_name}='AAPL'"
                    )

                if ticker_clean.isdigit():
                    return _build_yaml_error(
                        f"Invalid {arg_name}: '{ticker_clean}' appears to be numeric. Ticker must be a valid stock symbol. Example: {arg_name}='AAPL'"
                    )

                if ',' in ticker_clean or ';' in ticker_clean:
                    return _build_yaml_error(
                        f"Invalid {arg_name} format: '{ticker_clean}' contains multiple tickers. Pass one ticker at a time. Example: {arg_name}='AAPL'"
                    )

            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_numeric_arg(
    arg_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    positive_only: bool = False
) -> Callable:
    """Decorator to validate numeric arguments (int or float).

    Args:
        arg_name: Name of the numeric parameter to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        positive_only: If True, only allow positive numbers

    Returns:
        Decorator that validates numeric argument before calling the function

    Example:
        @validate_numeric_arg("weight", min_value=0, max_value=1)
        def set_weight(weight: float) -> str:
            # weight is guaranteed to be between 0 and 1
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            value = _get_arg_value(arg_name, args, kwargs, func)

            if value is not None:
                if not isinstance(value, (int, float)):
                    return _build_yaml_error(f"Invalid {arg_name} type: expected number, got {type(value).__name__}")

                if positive_only and value <= 0:
                    return _build_yaml_error(f"Invalid {arg_name}: must be positive, got {value}")

                if min_value is not None and value < min_value:
                    return _build_yaml_error(f"Invalid {arg_name}: must be >= {min_value}, got {value}")

                if max_value is not None and value > max_value:
                    return _build_yaml_error(f"Invalid {arg_name}: must be <= {max_value}, got {value}")

            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_enum_arg(arg_name: str, allowed_values: List[str]) -> Callable:
    """Decorator to validate string argument is one of allowed values.

    Args:
        arg_name: Name of the parameter to validate
        allowed_values: List of allowed string values

    Returns:
        Decorator that validates enum argument before calling the function

    Example:
        @validate_enum_arg("sort_by", ["price", "volume", "market_cap"])
        def get_stocks(sort_by: str) -> str:
            # sort_by is guaranteed to be valid
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            value = _get_arg_value(arg_name, args, kwargs, func)

            # Check if required argument is missing
            if value is None:
                return _build_yaml_error(
                    f"Missing required argument: '{arg_name}'. Must be one of: {allowed_values}. Example: {arg_name}='{allowed_values[0]}'"
                )

            if value is not None:
                if not isinstance(value, str):
                    return _build_yaml_error(f"Invalid {arg_name} type: expected string, got {type(value).__name__}")

                if value not in allowed_values:
                    return _build_yaml_error(f"Invalid {arg_name}: '{value}' not in allowed values {allowed_values}")

            return func(*args, **kwargs)
        return wrapper
    return decorator


def _validate_portfolio_ticker(ticker: str, data: Any, arg_name: str) -> Optional[str]:
    """Helper to validate single ticker entry in portfolio dict.

    Returns error string if invalid, None if valid.
    """
    # Check ticker is string
    if not isinstance(ticker, str):
        return f"Invalid ticker type in {arg_name}: expected string, got {type(ticker).__name__}. Example: {arg_name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"

    # Check data is dict
    if not isinstance(data, dict):
        return f"Invalid structure for ticker '{ticker}': expected dict with 'allocation' and 'position', got {type(data).__name__}. Example: {arg_name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"

    # Check has allocation
    if 'allocation' not in data:
        return f"Missing 'allocation' for ticker '{ticker}'. Example: {arg_name}={{{ticker}: {{'allocation': 0.5, 'position': 'long'}}}}"

    # Check has position
    if 'position' not in data:
        return f"Missing 'position' for ticker '{ticker}'. Example: {arg_name}={{{ticker}: {{'allocation': {data['allocation']}, 'position': 'long'}}}}"

    # Validate allocation is numeric
    allocation = data['allocation']
    if not isinstance(allocation, (int, float)):
        return f"Invalid allocation type for ticker '{ticker}': expected number, got {type(allocation).__name__}. Example: {arg_name}={{{ticker}: {{'allocation': 0.5, 'position': '{data['position']}'}}}}"

    # Validate allocation range (0 to 1)
    if not (0 <= allocation <= 1):
        return f"Invalid allocation value for ticker '{ticker}': {allocation} (must be between 0 and 1). Example: {arg_name}={{{ticker}: {{'allocation': 0.5, 'position': '{data['position']}'}}}}"

    # Validate position is valid
    position = data['position']
    if not isinstance(position, str):
        return f"Invalid position type for ticker '{ticker}': expected string, got {type(position).__name__}. Example: {arg_name}={{{ticker}: {{'allocation': {allocation}, 'position': 'long'}}}}"

    if position.lower() not in ['long', 'short']:
        return f"Invalid position value for ticker '{ticker}': '{position}' (must be 'long' or 'short'). Example: {arg_name}={{{ticker}: {{'allocation': {allocation}, 'position': 'long'}}}}"

    return None  # Valid


def validate_portfolio_dict(arg_name: str = "portfolio_dict") -> Callable:
    """Decorator to validate portfolio_dict argument structure.

    Args:
        arg_name: Name of the portfolio parameter to validate (default: "portfolio_dict")

    Returns:
        Decorator that validates portfolio dict structure before calling the function

    Example:
        @validate_portfolio_dict()
        def calculate_metrics(portfolio_dict: dict) -> str:
            # portfolio_dict is guaranteed to have valid structure
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            portfolio = _get_arg_value(arg_name, args, kwargs, func)

            if portfolio is not None:
                # Check type is dict
                if not isinstance(portfolio, dict):
                    return _build_yaml_error(
                        f"Invalid {arg_name} type: expected dict, got {type(portfolio).__name__}. Example: {arg_name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"
                    )

                # Check not empty
                if not portfolio:
                    return _build_yaml_error(
                        f"Empty {arg_name} provided. Example: {arg_name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"
                    )

                # Validate each ticker entry
                for ticker, data in portfolio.items():
                    error = _validate_portfolio_ticker(ticker, data, arg_name)
                    if error:
                        return _build_yaml_error(error)

            return func(*args, **kwargs)
        return wrapper
    return decorator


def _generate_example_for_arg(arg_name: str) -> str:
    """Generate example value for argument based on name."""
    if 'ticker' in arg_name:
        return f"{arg_name}='AAPL'"
    elif 'factor' in arg_name:
        return f"{arg_name}='growth'"
    elif 'portfolio' in arg_name:
        return f"{arg_name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"
    elif 'data_type' in arg_name:
        return f"{arg_name}='stock_news'"
    else:
        return f"{arg_name}=<value>"


def validate_required_args(*required_arg_names: str) -> Callable:
    """Decorator to validate that required arguments are present.

    Args:
        *required_arg_names: Names of required parameters

    Returns:
        Decorator that checks all required args are present before calling the function

    Example:
        @validate_required_args('ticker', 'factor')
        def get_data(ticker: str, factor: str, optional: str = None) -> str:
            # ticker and factor are guaranteed to be present
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)

            # Build dict of all provided arguments
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            provided_args = set(bound_args.arguments.keys())

            # Check each required arg
            missing_args = []
            for required_arg in required_arg_names:
                if required_arg not in provided_args or bound_args.arguments.get(required_arg) is None:
                    missing_args.append(required_arg)

            if missing_args:
                examples = [_generate_example_for_arg(arg) for arg in missing_args]
                example_str = ", ".join(examples)
                return _build_yaml_error(f"Missing required argument(s): {missing_args}. Example: {example_str}")

            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_tickers_arg(arg_name: str = "tickers") -> Callable:
    """Decorator to validate a list of tickers argument.

    Args:
        arg_name: Name of the tickers parameter to validate (default: "tickers")

    Returns:
        Decorator that validates tickers list format before calling the function

    Example:
        @validate_tickers_arg()
        def get_ticker_data(tickers: List[str]) -> str:
            # tickers is guaranteed to be valid list of strings
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tickers = _get_arg_value(arg_name, args, kwargs, func)

            if tickers is None:
                return _build_yaml_error(
                    f"Missing required argument: '{arg_name}'. Example: {arg_name}=['AAPL', 'MSFT']"
                )

            if not isinstance(tickers, list):
                return _build_yaml_error(
                    f"Invalid {arg_name} type: expected list, got {type(tickers).__name__}. Example: {arg_name}=['AAPL', 'MSFT']"
                )

            if not tickers:
                return _build_yaml_error(
                    f"Empty {arg_name} list provided. Example: {arg_name}=['AAPL', 'MSFT']"
                )

            # Validate each ticker in the list
            for ticker in tickers:
                if not isinstance(ticker, str):
                    return _build_yaml_error(
                        f"Invalid ticker type in {arg_name}: expected string, got {type(ticker).__name__}. Example: {arg_name}=['AAPL', 'MSFT']"
                    )

                ticker_clean = ticker.strip().upper()

                if not ticker_clean:
                    return _build_yaml_error(
                        f"Empty ticker string found in {arg_name}. Example: {arg_name}=['AAPL', 'MSFT']"
                    )

                if ticker_clean.isdigit():
                    return _build_yaml_error(
                        f"Invalid ticker in {arg_name}: '{ticker_clean}' appears to be numeric. Tickers must be valid stock symbols. Example: {arg_name}=['AAPL', 'MSFT']"
                    )

            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_simulation_data_range(data_extractor: Optional[Callable] = None) -> Callable:
    """Decorator to log the date range of data being used in simulation/production mode.

    This decorator inspects the _simulation_date parameter and logs information about
    the data range being used by the tool. It helps with debugging simulation issues.

    Args:
        data_extractor: Optional callable that extracts data (pd.Series/DataFrame) from
                       function execution context for date range inspection.
                       Function signature: data_extractor(result, kwargs, locals_dict)
                       If not provided, logs only simulation mode status.

    Returns:
        Decorator that logs simulation data range information

    Example:
        @log_simulation_data_range()
        def get_ticker_data(ticker: str, _simulation_date: Optional[datetime] = None) -> str:
            # Will log simulation mode automatically
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get _simulation_date from kwargs
            _simulation_date = kwargs.get('_simulation_date')

            # Determine mode
            mode = "SIMULATION" if _simulation_date else "PRODUCTION"

            # Get function name and key args for logging
            func_name = func.__name__

            # Build log message with key arguments (exclude _simulation_date)
            key_args = []
            if 'ticker' in kwargs:
                key_args.append(f"{kwargs['ticker']}")
            elif 'portfolio_dict' in kwargs:
                key_args.append("portfolio")
            if 'data_type' in kwargs:
                key_args.append(f"{kwargs['data_type']}")
            if 'statement_type' in kwargs:
                key_args.append(f"{kwargs['statement_type']}")

            args_str = f"({', '.join(key_args)})" if key_args else ""

            # Log function call with date info
            from datetime import datetime as dt
            if _simulation_date:
                cutoff_str = _simulation_date.date()
                print(f"[{mode}] {func_name}{args_str} | Cutoff: {cutoff_str}")
            else:
                print(f"[{mode}] {func_name}{args_str}")

            # Execute the function
            result = func(*args, **kwargs)

            # In simulation mode, try to extract and log actual data ranges used
            if _simulation_date:
                try:
                    data_ranges_found = []

                    # Check if price_data was passed in kwargs (from @with_bulk_price_data decorator)
                    price_data = kwargs.get('price_data')
                    if price_data is not None:
                        if isinstance(price_data, dict):
                            # Dict of ticker -> Series
                            for ticker_key, series in price_data.items():
                                if isinstance(series, pd.Series) and hasattr(series, 'index'):
                                    if isinstance(series.index, pd.DatetimeIndex) and len(series) > 0:
                                        data_ranges_found.append({
                                            'name': f'price_data[{ticker_key}]',
                                            'start': series.index.min(),
                                            'end': series.index.max(),
                                            'count': len(series),
                                            'cutoff_ok': series.index.max() <= _simulation_date
                                        })
                        elif isinstance(price_data, pd.Series) and hasattr(price_data, 'index'):
                            # Single Series
                            if isinstance(price_data.index, pd.DatetimeIndex) and len(price_data) > 0:
                                data_ranges_found.append({
                                    'name': 'price_data',
                                    'start': price_data.index.min(),
                                    'end': price_data.index.max(),
                                    'count': len(price_data),
                                    'cutoff_ok': price_data.index.max() <= _simulation_date
                                })

                    # Also check portfolio_dict if it exists (for portfolio tools)
                    portfolio = kwargs.get('portfolio_dict')
                    if portfolio and isinstance(portfolio, dict):
                        ticker_list = list(portfolio.keys())
                        if ticker_list:
                            data_ranges_found.append({
                                'name': f'portfolio ({len(ticker_list)} tickers)',
                                'tickers': ticker_list[:5],  # Show first 5
                                'total': len(ticker_list)
                            })

                    # Print data ranges if found
                    if data_ranges_found:
                        print(f"  📅 ACTUAL DATA USED:")
                        for dr in data_ranges_found:
                            if 'start' in dr:
                                cutoff_status = "✅" if dr.get('cutoff_ok', True) else "⚠️ EXCEEDS CUTOFF"
                                print(f"    • {dr['name']}: {dr['start'].date()} → {dr['end'].date()} "
                                      f"({dr['count']} points) {cutoff_status}")
                            elif 'tickers' in dr:
                                tickers_shown = ', '.join(dr['tickers'])
                                if dr['total'] > 5:
                                    tickers_shown += f", ... (+{dr['total'] - 5} more)"
                                print(f"    • {dr['name']}: {tickers_shown}")
                except Exception:
                    # Don't fail the function if logging fails
                    pass

            # Try to extract data for date range logging (if extractor provided)
            if data_extractor:
                try:
                    data = data_extractor(kwargs)
                    if data is not None and hasattr(data, 'index') and len(data) > 0:
                        if isinstance(data.index, pd.DatetimeIndex):
                            print(f"[{mode}] Data range: {data.index[0].date()} → {data.index[-1].date()} ({len(data)} days)")
                except Exception:
                    pass  # Silently fail if data extraction doesn't work

            return result
        return wrapper
    return decorator
