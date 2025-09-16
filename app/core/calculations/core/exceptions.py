"""Custom exceptions for calculations_v2"""

class CalculationsError(Exception):
    """Base exception for calculations module"""
    pass

class DataFetchError(CalculationsError):
    """Raised when data fetching fails"""
    pass

class InsufficientDataError(CalculationsError):
    """Raised when there's not enough data for calculation"""
    pass

class InvalidParameterError(CalculationsError):
    """Raised when invalid parameters are provided"""
    pass

class CalculationError(CalculationsError):
    """Raised when calculation fails"""
    pass
