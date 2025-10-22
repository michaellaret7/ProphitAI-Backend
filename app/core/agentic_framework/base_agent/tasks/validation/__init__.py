"""Context-aware validation module for task completion.

This module provides simple, boolean-based validation with context-aware
error detection to avoid false positives in finance domain text.
"""

from .completion_validator import CompletionValidator
from .error_detection import has_error, has_error_in_dict, has_error_in_result
from .patterns import SAFE_PHRASES, ERROR_PATTERNS

__all__ = [
    'CompletionValidator',
    'has_error',
    'has_error_in_dict',
    'has_error_in_result',
    'SAFE_PHRASES',
    'ERROR_PATTERNS',
]
