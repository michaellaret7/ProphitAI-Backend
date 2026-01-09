"""
calculations_v2: Next-generation calculations module
"""

from .core import (
    CalculationsError,
    DataFetchError,
    InsufficientDataError,
    InvalidParameterError,
    CalculationError,
)

__version__ = "2.0.0"
__all__ = [
    "CalculationsError",
    "DataFetchError",
    "InsufficientDataError",
    "InvalidParameterError",
    "CalculationError",
]
