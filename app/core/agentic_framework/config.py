"""
Agentic Framework Configuration

Feature flags for gradual refactoring rollout.
"""


class RefactoringFlags:
    """Feature flags for refactoring phases."""

    # Phase 1-3: New component flags
    USE_NEW_VALIDATOR = False  # Default: Use old validator
    USE_NEW_RESULT_PARSER = False  # Default: Use old parser
    USE_CALLBACK_PATTERN = False  # Default: Use old event system

    # Phase 4: Validator migration flags
    ENABLE_PARALLEL_VALIDATION = False  # Compare old vs new validator
    LOG_VALIDATOR_MISMATCHES = False  # Log differences
    KEEP_OLD_VALIDATOR_FALLBACK = False  # Keep old validator as safety net

    @classmethod
    def enable_new_validator(cls):
        """Enable new validator with parallel validation for safety."""
        cls.USE_NEW_VALIDATOR = True
        cls.ENABLE_PARALLEL_VALIDATION = True
        cls.LOG_VALIDATOR_MISMATCHES = True