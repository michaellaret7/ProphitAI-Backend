"""
calculations_v2: Next-generation calculations module

This package is under active development. During Phase 1, we expose only
stable core exceptions to avoid import errors while scaffolding.
"""

from .core import (
    CalculationsError,
    DataFetchError,
    InsufficientDataError,
    InvalidParameterError,
    CalculationError,
    DataService,
)

__version__ = "2.0.0"
__all__ = [
    "CalculationsError",
    "DataFetchError",
    "InsufficientDataError",
    "InvalidParameterError",
    "CalculationError",
    "DataService",
]
