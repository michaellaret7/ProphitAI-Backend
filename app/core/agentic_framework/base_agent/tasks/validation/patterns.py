"""Validation patterns for context-aware error detection.

This module contains pattern constants for detecting errors while avoiding
false positives in finance domain text (e.g., "tracking error", "Ameren").
"""

# Finance-specific phrases that contain "error" but are NOT errors
SAFE_PHRASES = [
    r'tracking error',           # Financial metric for portfolio deviation
    r'margin.{0,5}error',        # "margin of error" in statistics
    r'standard error',           # Statistical measure
    r'ameren',                   # Stock ticker AEE (Ameren Corp) contains "error"
    r'error correction model',   # Economic model (ECM)
    r'mean squared error',       # Statistical metric (MSE)
    r'root mean squared error',  # Statistical metric (RMSE)
    r'forecast error',           # Expected deviation in predictions
    r'estimation error',         # Statistical concept
    r'measurement error',        # Data quality concept
    r'type i error',            # Statistical concept (false positive)
    r'type ii error',           # Statistical concept (false negative)
]

# Actual error patterns that indicate failures
ERROR_PATTERNS = [
    r'^error:',                  # Error message at start
    r'^error\s',                 # "Error" at start followed by space
    r'error occurred',           # Common error phrase
    r'error during',             # "error during execution"
    r'encountered.*error',       # "encountered an error"
    r'\bfailed to\b',           # Failed operations
    r'\bfailure\b',             # Failure notifications
    r'^failed:',                # Failed at start
    r'exception:',              # Exception messages
    r'exception occurred',      # Exception notifications
    r'^exception\s',            # "Exception" at start
    r'unhandled exception',     # Unhandled errors
    r'could not',               # "could not connect"
    r'unable to',               # "unable to process"
    r'cannot\s',                # "cannot access"
    r'invalid\s',               # "invalid input"
    r'not found',               # "file not found"
]
