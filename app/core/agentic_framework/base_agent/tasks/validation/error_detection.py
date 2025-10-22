"""Context-aware error detection for finance domain.

This module provides functions to detect errors in text while avoiding
false positives from finance-specific terminology.
"""

import re
from typing import Any, Dict
from .patterns import SAFE_PHRASES, ERROR_PATTERNS


def has_error(text: str) -> bool:
    """Check if text contains an error, with context awareness.

    Args:
        text: Text to check for errors

    Returns:
        True if text contains an error, False otherwise

    Examples:
        >>> has_error("tracking error is 2.5%")
        False  # Finance term, not an error

        >>> has_error("Error: Connection failed")
        True  # Actual error message

        >>> has_error("Ameren stock price")
        False  # Stock ticker, not an error
    """
    if not text or not isinstance(text, str):
        return False

    text_lower = text.lower()

    # Check safe phrases FIRST to prevent false positives
    for safe_pattern in SAFE_PHRASES:
        if re.search(safe_pattern, text_lower, re.IGNORECASE):
            return False

    # Now check for actual error patterns
    for error_pattern in ERROR_PATTERNS:
        if re.search(error_pattern, text_lower, re.MULTILINE | re.IGNORECASE):
            return True

    return False


def has_error_in_dict(result: Dict[str, Any]) -> bool:
    """Check if a dictionary result indicates an error.

    Args:
        result: Dictionary to check (typically a parsed tool result)

    Returns:
        True if result indicates error, False otherwise

    Examples:
        >>> has_error_in_dict({"success": False, "error": "Failed"})
        True

        >>> has_error_in_dict({"success": True, "data": {"value": 100}})
        False
    """
    if not isinstance(result, dict):
        return False

    # Check success field
    if 'success' in result and result['success'] is False:
        return True

    # Check for error field (case-insensitive)
    error_keys = [k for k in result.keys() if k.lower() in ('error', 'exception')]
    if error_keys:
        return True

    # Check error field content if present
    if 'error' in result and result['error']:
        return True

    return False


def has_error_in_result(tool_result: Any) -> bool:
    """Check if a tool result (any type) indicates an error.

    This is a unified function that handles all result types:
    - Dicts: Check success field and error keys
    - Strings: Check for error patterns
    - Exceptions: Always considered errors
    - None: Considered an error

    Args:
        tool_result: Tool result of any type

    Returns:
        True if result indicates error, False otherwise

    Examples:
        >>> has_error_in_result({"success": False})
        True

        >>> has_error_in_result("Error: timeout")
        True

        >>> has_error_in_result(ValueError("bad input"))
        True

        >>> has_error_in_result(None)
        True

        >>> has_error_in_result("Data retrieved successfully")
        False
    """
    # Exception objects are always errors
    if isinstance(tool_result, Exception):
        return True

    # None is considered an error
    if tool_result is None:
        return True

    # Check dicts
    if isinstance(tool_result, dict):
        return has_error_in_dict(tool_result)

    # Check strings
    if isinstance(tool_result, str):
        return has_error(tool_result)

    # Other types (int, float, list, etc.) are not errors
    return False
