"""Centralized tool result parser for standardized error handling.

This module provides a single source of truth for parsing tool results
into the standardized dict format used across the agent framework.
"""

import re
import yaml
from typing import Any, Dict


def parse_tool_result(observation: Any, verbose: bool = False) -> Dict[str, Any]:
    """Parse tool result into standardized dict format.

    All tools return YAML strings with {"success": bool, "data"/"error": ...} format.
    This function parses various response types into a consistent dict structure.

    Args:
        observation: Raw tool output (YAML string, dict, or other)
        verbose: Whether to print debug messages

    Returns:
        Dict with 'success' bool and 'data'/'error' fields:
        - {"success": True, "data": ...} on success
        - {"success": False, "error": "..."} on failure

    Examples:
        >>> parse_tool_result("success: true\\ndata: {foo: bar}")
        {"success": True, "data": {"foo": "bar"}}

        >>> parse_tool_result({"success": False, "error": "Invalid"})
        {"success": False, "error": "Invalid"}

        >>> parse_tool_result("Error: Tool failed")
        {"success": False, "error": "Error: Tool failed"}
    """
    # Already a dict - return as-is
    if isinstance(observation, dict):
        # Ensure success field exists (default to True if missing)
        if 'success' not in observation:
            if verbose:
                print(f"⚠️ Tool response missing 'success' field, inferring from 'error' presence")
            # If has error field, assume failure
            if 'error' in observation:
                observation['success'] = False
            else:
                observation['success'] = True
        return observation

    # Try to parse YAML string
    if isinstance(observation, str):
        try:
            parsed = yaml.safe_load(observation)
            if isinstance(parsed, dict):
                # Ensure success field exists
                if 'success' not in parsed:
                    if verbose:
                        print(f"⚠️ YAML response missing 'success' field, inferring from 'error' presence")
                    if 'error' in parsed:
                        parsed['success'] = False
                    else:
                        parsed['success'] = True
                return parsed
        except Exception as e:
            if verbose:
                print(f"⚠️ YAML parse failed: {e}, treating as plain string")
            pass

        # Plain string - check if it's an error message with improved pattern matching
        if re.match(r'^(error|failed|exception|unhandled)[:|\s]', observation, re.IGNORECASE):
            return {"success": False, "error": observation}
        else:
            # Treat as successful data return
            return {"success": True, "data": observation}

    # Handle None
    if observation is None:
        return {"success": False, "error": "Tool returned None"}

    # Fallback for other types (Exception, etc.)
    if isinstance(observation, Exception):
        return {"success": False, "error": str(observation)}

    # Other types - treat as successful data
    return {"success": True, "data": observation}
