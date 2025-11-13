"""Tool input validator - simple helper class to replace decorator chains.

This module provides a clean, explicit way to validate tool inputs without
the complexity and overhead of stacked decorators. Follows KISS principle.

Usage:
    def my_tool(portfolio_dict: dict, metric: str) -> str:
        v = ToolValidator()
        v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
        v.require_enum('metric', metric, ['vol', 'var'])

        if not v.is_valid():
            return v.error_response()

        # Get validated/normalized values
        portfolio_dict = v.get('portfolio_dict')
        metric = v.get('metric')

        # Business logic...
"""

import yaml
from typing import Optional, List, Any, Dict


class ToolValidator:
    """Validates and normalizes tool inputs.

    This class provides a simple, explicit way to validate tool arguments
    without decorator overhead. Validation is performed in a single pass,
    and normalized values are stored for retrieval.

    Attributes:
        errors: List of validation error messages
        _values: Dict of validated/normalized values
    """

    def __init__(self):
        self.errors: List[str] = []
        self._values: Dict[str, Any] = {}

    def require_portfolio(
        self,
        name: str,
        value: Optional[dict],
        normalize: bool = True
    ) -> 'ToolValidator':
        """Validate required portfolio dict and optionally normalize it.

        Args:
            name: Parameter name (for error messages)
            value: Portfolio dict to validate
            normalize: If True, applies canonical_portfolio transformation

        Returns:
            Self for method chaining

        Validates:
            - Value is not None
            - Value is a dict
            - Dict is not empty
            - Each ticker entry has 'allocation' and 'position'
            - Allocation is numeric and in range [0, 1]
            - Position is 'long' or 'short'
        """
        if value is None:
            self.errors.append(
                f"Missing required argument: '{name}'. Please try again with a valid portfolio. "
                f"Example: {name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}, "
                f"'MSFT': {{'allocation': 0.5, 'position': 'long'}}}}"
            )
            return self

        if not isinstance(value, dict):
            self.errors.append(
                f"Invalid {name} type: expected dict, got {type(value).__name__}. Please try again. "
                f"Example: {name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"
            )
            return self

        if not value:
            self.errors.append(
                f"Empty {name} provided. Please try again with at least one ticker. "
                f"Example: {name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"
            )
            return self

        # Validate each ticker entry
        for ticker, data in value.items():
            if not isinstance(ticker, str):
                self.errors.append(
                    f"Invalid ticker in {name}: expected string, got {type(ticker).__name__}. Please try again. "
                    f"Example: {name}={{'AAPL': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            if not isinstance(data, dict):
                self.errors.append(
                    f"Invalid structure for ticker '{ticker}' in {name}: "
                    f"expected dict with 'allocation' and 'position'. Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            # Check allocation
            if 'allocation' not in data:
                self.errors.append(
                    f"Missing 'allocation' for ticker '{ticker}' in {name}. Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            allocation = data['allocation']
            if not isinstance(allocation, (int, float)):
                self.errors.append(
                    f"Invalid allocation type for ticker '{ticker}' in {name}: "
                    f"expected number, got {type(allocation).__name__}. Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            if not (0 <= allocation <= 1):
                self.errors.append(
                    f"Invalid allocation value for ticker '{ticker}' in {name}: "
                    f"{allocation} (must be between 0 and 1). Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            # Check position
            if 'position' not in data:
                self.errors.append(
                    f"Missing 'position' for ticker '{ticker}' in {name}. Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            position = data['position']
            if not isinstance(position, str):
                self.errors.append(
                    f"Invalid position type for ticker '{ticker}' in {name}: "
                    f"expected string, got {type(position).__name__}. Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

            if position.lower() not in ['long', 'short']:
                self.errors.append(
                    f"Invalid position value for ticker '{ticker}' in {name}: "
                    f"'{position}' (must be 'long' or 'short'). Please try again. "
                    f"Example: {name}={{'{ticker}': {{'allocation': 0.5, 'position': 'long'}}}}"
                )
                return self

        # Normalize if requested and no errors
        if normalize and not self.errors:
            try:
                from app.utils.gpt_parser import canonical_portfolio
                self._values[name] = canonical_portfolio(value)
            except Exception as e:
                self.errors.append(f"Failed to normalize {name}: {str(e)}")
                return self
        else:
            self._values[name] = value

        return self

    def require_enum(
        self,
        name: str,
        value: Optional[str],
        allowed: List[str]
    ) -> 'ToolValidator':
        """Validate required enum value.

        Args:
            name: Parameter name (for error messages)
            value: Value to validate
            allowed: List of allowed values

        Returns:
            Self for method chaining

        Validates:
            - Value is not None
            - Value is a string
            - Value is in allowed list
        """
        if value is None:
            self.errors.append(
                f"Missing required argument: '{name}'. Please try again with one of: {allowed}. "
                f"Example: {name}='{allowed[0]}'"
            )
            return self

        if not isinstance(value, str):
            self.errors.append(
                f"Invalid {name} type: expected string, got {type(value).__name__}. Please try again. "
                f"Example: {name}='{allowed[0]}'"
            )
            return self

        if value not in allowed:
            self.errors.append(
                f"Invalid {name}: '{value}' not in allowed values {allowed}. Please try again. "
                f"Example: {name}='{allowed[0]}'"
            )
            return self

        self._values[name] = value
        return self

    def require_ticker(
        self,
        name: str,
        value: Optional[str]
    ) -> 'ToolValidator':
        """Validate required ticker symbol.

        Args:
            name: Parameter name (for error messages)
            value: Ticker symbol to validate

        Returns:
            Self for method chaining

        Validates:
            - Value is not None
            - Value is a string
            - Value is not empty
            - Value doesn't start with '[' or '{' (list/dict indicators)
            - Value is not purely numeric
            - Value doesn't contain multiple tickers (no commas/semicolons)
        """
        if value is None:
            self.errors.append(
                f"Missing required argument: '{name}'. Please try again with a valid ticker symbol. "
                f"Example: {name}='AAPL'"
            )
            return self

        if not isinstance(value, str):
            self.errors.append(
                f"Invalid {name} type: expected string, got {type(value).__name__}. Please try again. "
                f"Example: {name}='AAPL'"
            )
            return self

        ticker = value.strip().upper()

        if not ticker:
            self.errors.append(
                f"Empty {name} string provided. Please try again with a valid ticker. "
                f"Example: {name}='AAPL'"
            )
            return self

        # Check if it looks like a list or dict was passed
        if ticker.startswith('[') or ticker.startswith('{'):
            self.errors.append(
                f"Invalid {name} format: appears to be a list or dict ('{ticker}'). "
                f"Please try again with a single ticker string. "
                f"Example: {name}='AAPL'"
            )
            return self

        if ticker.isdigit():
            self.errors.append(
                f"Invalid {name}: '{ticker}' appears to be numeric. "
                f"Please try again with a valid stock symbol. "
                f"Example: {name}='AAPL'"
            )
            return self

        if ',' in ticker or ';' in ticker:
            self.errors.append(
                f"Invalid {name} format: '{ticker}' contains multiple tickers. "
                f"Please try again with one ticker at a time. "
                f"Example: {name}='AAPL'"
            )
            return self

        self._values[name] = ticker
        return self

    def require_tickers(
        self,
        name: str,
        value: Optional[List[str]]
    ) -> 'ToolValidator':
        """Validate required list of ticker symbols.

        Args:
            name: Parameter name (for error messages)
            value: List of ticker symbols to validate

        Returns:
            Self for method chaining

        Validates:
            - Value is not None
            - Value is a list
            - List is not empty
            - Each ticker is a valid string
        """
        if value is None:
            self.errors.append(
                f"Missing required argument: '{name}'. Please try again with a list of ticker symbols. "
                f"Example: {name}=['AAPL', 'MSFT', 'GOOGL']"
            )
            return self

        if not isinstance(value, list):
            self.errors.append(
                f"Invalid {name} type: expected list, got {type(value).__name__}. Please try again. "
                f"Example: {name}=['AAPL', 'MSFT', 'GOOGL']"
            )
            return self

        if not value:
            self.errors.append(
                f"Empty {name} list provided. Please try again with at least one ticker. "
                f"Example: {name}=['AAPL', 'MSFT']"
            )
            return self

        # Validate each ticker
        valid_tickers = []
        for ticker in value:
            if not isinstance(ticker, str):
                self.errors.append(
                    f"Invalid ticker type in {name}: expected string, "
                    f"got {type(ticker).__name__}. Please try again. "
                    f"Example: {name}=['AAPL', 'MSFT']"
                )
                return self

            ticker_clean = ticker.strip().upper()

            if not ticker_clean:
                self.errors.append(
                    f"Empty ticker string found in {name}. Please try again. "
                    f"Example: {name}=['AAPL', 'MSFT']"
                )
                return self

            if ticker_clean.isdigit():
                self.errors.append(
                    f"Invalid ticker in {name}: '{ticker_clean}' appears to be numeric. "
                    f"Please try again with valid ticker symbols. "
                    f"Example: {name}=['AAPL', 'MSFT']"
                )
                return self

            valid_tickers.append(ticker_clean)

        self._values[name] = valid_tickers
        return self

    def require_numeric(
        self,
        name: str,
        value: Optional[float],
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        positive_only: bool = False
    ) -> 'ToolValidator':
        """Validate required numeric value.

        Args:
            name: Parameter name (for error messages)
            value: Numeric value to validate
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            positive_only: If True, only allow positive numbers

        Returns:
            Self for method chaining

        Validates:
            - Value is not None
            - Value is numeric (int or float)
            - Value meets min/max constraints
            - Value is positive if positive_only=True
        """
        if value is None:
            example_val = min_val if min_val is not None else 1
            self.errors.append(
                f"Missing required argument: '{name}'. Please try again with a valid number. "
                f"Example: {name}={example_val}"
            )
            return self

        if not isinstance(value, (int, float)):
            example_val = min_val if min_val is not None else 1
            self.errors.append(
                f"Invalid {name} type: expected number, got {type(value).__name__}. Please try again. "
                f"Example: {name}={example_val}"
            )
            return self

        if positive_only and value <= 0:
            example_val = min_val if min_val and min_val > 0 else 1
            self.errors.append(
                f"Invalid {name}: must be positive, got {value}. Please try again. "
                f"Example: {name}={example_val}"
            )
            return self

        if min_val is not None and value < min_val:
            self.errors.append(
                f"Invalid {name}: must be >= {min_val}, got {value}. Please try again. "
                f"Example: {name}={min_val}"
            )
            return self

        if max_val is not None and value > max_val:
            self.errors.append(
                f"Invalid {name}: must be <= {max_val}, got {value}. Please try again. "
                f"Example: {name}={max_val}"
            )
            return self

        self._values[name] = value
        return self

    def optional_numeric(
        self,
        name: str,
        value: Optional[float],
        default: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        positive_only: bool = False
    ) -> 'ToolValidator':
        """Validate optional numeric value with default.

        Args:
            name: Parameter name (for error messages)
            value: Numeric value to validate (or None)
            default: Default value if None
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            positive_only: If True, only allow positive numbers

        Returns:
            Self for method chaining
        """
        if value is None:
            self._values[name] = default
            return self

        return self.require_numeric(name, value, min_val, max_val, positive_only)

    def optional_enum(
        self,
        name: str,
        value: Optional[str],
        allowed: List[str],
        default: str
    ) -> 'ToolValidator':
        """Validate optional enum value with default.

        Args:
            name: Parameter name (for error messages)
            value: Value to validate (or None)
            allowed: List of allowed values
            default: Default value if None

        Returns:
            Self for method chaining
        """
        if value is None:
            self._values[name] = default
            return self

        return self.require_enum(name, value, allowed)

    def is_valid(self) -> bool:
        """Check if all validations passed.

        Returns:
            True if no errors, False otherwise
        """
        return len(self.errors) == 0

    def error_response(self) -> str:
        """Get YAML error response with all validation errors.

        Returns:
            YAML-formatted error response string
        """
        return yaml.dump({
            "success": False,
            "error": "; ".join(self.errors)
        }, default_flow_style=False)

    def get(self, name: str) -> Any:
        """Get validated/normalized value.

        Args:
            name: Parameter name

        Returns:
            The validated/normalized value, or None if not found
        """
        return self._values.get(name)

    def get_all(self) -> Dict[str, Any]:
        """Get all validated/normalized values.

        Returns:
            Dictionary of all validated values
        """
        return self._values.copy()
