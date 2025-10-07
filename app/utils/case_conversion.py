"""
Utility functions for converting between snake_case and camelCase.

Used for transforming database models (snake_case) to API responses (camelCase).
"""

from typing import Dict, Any, List, Optional
import re


def snake_to_camel(snake_str: str) -> str:
    """
    Convert a snake_case string to camelCase.

    Args:
        snake_str: String in snake_case format (e.g., "user_name")

    Returns:
        String in camelCase format (e.g., "userName")

    Examples:
        >>> snake_to_camel("user_name")
        'userName'
        >>> snake_to_camel("total_return")
        'totalReturn'
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def dict_keys_to_camel(
    data: Dict[str, Any],
    key_map: Optional[Dict[str, str]] = None,
    recursive: bool = False
) -> Dict[str, Any]:
    """
    Convert dictionary keys from snake_case to camelCase.

    Args:
        data: Dictionary with snake_case keys
        key_map: Optional explicit mapping for specific keys (overrides auto-conversion)
        recursive: If True, recursively convert nested dicts and lists

    Returns:
        Dictionary with camelCase keys

    Examples:
        >>> dict_keys_to_camel({"user_name": "John", "total_count": 5})
        {'userName': 'John', 'totalCount': 5}

        >>> dict_keys_to_camel({"ytd_return": 10.5}, key_map={"ytd_return": "ytdReturn"})
        {'ytdReturn': 10.5}
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        # Use explicit mapping if provided, otherwise auto-convert
        if key_map and key in key_map:
            new_key = key_map[key]
        else:
            new_key = snake_to_camel(key)

        # Recursively convert nested structures if requested
        if recursive:
            if isinstance(value, dict):
                value = dict_keys_to_camel(value, key_map, recursive=True)
            elif isinstance(value, list):
                value = [
                    dict_keys_to_camel(item, key_map, recursive=True)
                    if isinstance(item, dict) else item
                    for item in value
                ]

        result[new_key] = value

    return result


def list_of_dicts_to_camel(
    data: List[Dict[str, Any]],
    key_map: Optional[Dict[str, str]] = None,
    recursive: bool = False
) -> List[Dict[str, Any]]:
    """
    Convert a list of dictionaries from snake_case to camelCase keys.

    Args:
        data: List of dictionaries with snake_case keys
        key_map: Optional explicit mapping for specific keys
        recursive: If True, recursively convert nested structures

    Returns:
        List of dictionaries with camelCase keys

    Examples:
        >>> data = [{"user_name": "John"}, {"user_name": "Jane"}]
        >>> list_of_dicts_to_camel(data)
        [{'userName': 'John'}, {'userName': 'Jane'}]
    """
    if not isinstance(data, list):
        return data

    return [
        dict_keys_to_camel(item, key_map, recursive)
        if isinstance(item, dict) else item
        for item in data
    ]


# Common key mappings for financial/portfolio APIs
PORTFOLIO_KEY_MAP = {
    'ytd_return': 'ytdReturn',
    'gross_exposure': 'grossExposure',
    'net_exposure': 'netExposure',
    'sharpe_ratio': 'sharpeRatio',
    'sortino_ratio': 'sortinoRatio',
    'max_drawdown': 'maxDrawdown',
    'up_capture': 'upCapture',
    'down_capture': 'downCapture',
    'var_95': 'var95',
    'rolling_12m_returns_daily': 'rolling12mReturnsDaily',
    'monthly_return_history': 'monthlyReturnHistory',
    'underwater_daily': 'underwaterDaily',
    'nav_performance_daily': 'navPerformanceDaily',
    'return_distribution': 'returnDistribution',
    'bin_start': 'binStart',
    'bin_end': 'binEnd',
    'ticker_name': 'tickerName',
    'risk_allocation': 'riskAllocation',
    'portfolio_allocation': 'portfolioAllocation',
    'portfolio_id': 'portfolioId',
    'is_current': 'isCurrent',
}
