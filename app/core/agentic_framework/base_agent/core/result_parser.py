"""Unified tool result parser - single source of truth for parsing tool outputs.

This replaces 4 different parsing implementations across the codebase:
- core/parser.py:parse_tool_result()
- core/utilities.py:execute_tool_safe()
- tasks/validator.py:_analyze_tool_success()
- tasks/execution_engine.py:_is_error_result()

All tools return YAML strings with {"success": bool, "data"/"error": ...} format.
This parser handles all result types (dict, str, YAML, Exception, None) consistently.
"""

import re
import yaml
from typing import Any, Dict, Optional


class ToolResultParser:
    """Unified parser for tool execution results.

    Provides consistent parsing and analysis of tool results across the framework.
    All results are normalized to: {"success": bool, "data": ..., "error": ...}

    Usage:
        parser = ToolResultParser(tool_result)
        if parser.is_success():
            data = parser.get_data()
        else:
            error = parser.get_error()
    """

    def __init__(self, result: Any, verbose: bool = False):
        """Initialize parser with a tool result.

        Args:
            result: Raw tool output (dict, str, YAML, Exception, None, etc.)
            verbose: Print debug messages during parsing
        """
        self.raw_result = result
        self.verbose = verbose
        self._parsed: Optional[Dict[str, Any]] = None
        self._parse()

    def _parse(self) -> None:
        """Parse the raw result into standardized dict format."""
        result = self.raw_result

        # Case 1: Already a dict - use as-is with validation
        if isinstance(result, dict):
            self._parsed = self._parse_dict(result)
            return

        # Case 2: Exception - convert to error dict
        if isinstance(result, Exception):
            self._parsed = {
                "success": False,
                "error": str(result),
                "error_type": type(result).__name__
            }
            return

        # Case 3: None - treat as error
        if result is None:
            self._parsed = {
                "success": False,
                "error": "Tool returned None"
            }
            return

        # Case 4: String - try YAML parse, then plain string
        if isinstance(result, str):
            self._parsed = self._parse_string(result)
            return

        # Case 5: Other types (int, float, list, etc.) - treat as successful data
        self._parsed = {
            "success": True,
            "data": result
        }

    def _parse_dict(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse dict result, ensuring 'success' field exists."""
        # Make a copy to avoid mutating original
        parsed = result.copy()

        # Normalize error field (handle case-insensitive variations)
        # Check for: 'error', 'Error', 'ERROR', 'exception', 'Exception', etc.
        error_like_keys = [k for k in parsed.keys() if k.lower() in ('error', 'exception')]
        if error_like_keys and 'error' not in parsed:
            # Move Error/Exception to lowercase 'error'
            parsed['error'] = parsed.pop(error_like_keys[0])

        # Ensure success field exists
        if 'success' not in parsed:
            if self.verbose:
                print("⚠️ Tool response missing 'success' field, inferring from 'error' presence")

            # Infer success from presence of error field (now normalized to lowercase)
            if 'error' in parsed:
                parsed['success'] = False
            else:
                parsed['success'] = True

        return parsed

    def _parse_string(self, result: str) -> Dict[str, Any]:
        """Parse string result - try YAML first, then check error patterns."""
        # Try YAML parsing first for structured data
        try:
            parsed = yaml.safe_load(result)
            # If YAML parsing returns a dict, use it
            if isinstance(parsed, dict):
                return self._parse_dict(parsed)
            # If YAML returns a string, fall through to error pattern checking
        except Exception as e:
            if self.verbose:
                print(f"⚠️ YAML parse failed: {e}, checking for error patterns")

        # Check if string looks like an error message
        # This catches plain error strings like "Error: message" or "Failed to connect"
        if re.match(r'^(error|failed|exception|unhandled)[:|\s]', result, re.IGNORECASE):
            return {
                "success": False,
                "error": result
            }

        # Otherwise treat as successful data
        return {
            "success": True,
            "data": result
        }

    def parse(self) -> Dict[str, Any]:
        """Get the parsed result as a standardized dict.

        Returns:
            Dict with structure:
            - {"success": True, "data": ...} on success
            - {"success": False, "error": "..."} on failure
        """
        return self._parsed

    def is_success(self) -> bool:
        """Check if the result indicates success.

        Returns:
            True if success, False if error/failure
        """
        return self._parsed.get('success', False)

    def is_error(self) -> bool:
        """Check if the result indicates an error.

        Returns:
            True if error/failure, False if success
        """
        return not self.is_success()

    def get_data(self) -> Any:
        """Extract data from successful result.

        Returns:
            The data field if present, otherwise None
        """
        return self._parsed.get('data')

    def get_error(self) -> Optional[str]:
        """Extract error message from failed result.

        Returns:
            Error message string if present, otherwise None
        """
        return self._parsed.get('error')

    def get_error_type(self) -> Optional[str]:
        """Get the type of error if result was an Exception.

        Returns:
            Exception class name if result was Exception, otherwise None
        """
        return self._parsed.get('error_type')

    def has_data(self) -> bool:
        """Check if result contains data field.

        Returns:
            True if 'data' field exists, False otherwise
        """
        return 'data' in self._parsed

    def has_error(self) -> bool:
        """Check if result contains error field.

        Returns:
            True if 'error' field exists, False otherwise
        """
        return 'error' in self._parsed

    def summarize(self) -> str:
        """Get a brief summary of the result for logging.

        Returns:
            Human-readable summary string
        """
        if self.is_success():
            data = self.get_data()
            if data is None:
                return "Success (no data)"
            elif isinstance(data, dict):
                return f"Success with {len(data)} fields"
            elif isinstance(data, list):
                return f"Success with {len(data)} items"
            else:
                return f"Success: {str(data)[:50]}"
        else:
            error = self.get_error()
            return f"Error: {error[:100] if error else 'Unknown error'}"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ToolResultParser(success={self.is_success()}, data={self.has_data()}, error={self.has_error()})"

