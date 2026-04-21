"""Pre-backtest integrity checks for constructed strategies.

Catches template-scaffold leakage (unchanged template imports, wrong class
names, mismatched ``MANIFEST.strategy_id``) BEFORE the backtest runs so
the validator doesn't spend compute on a strategy that would silently
execute generic template logic.
"""

from prophitai_algo_trading.integrity.scaffold_check import (
    IntegrityViolation,
    check_scaffold_integrity,
)

__all__ = ["IntegrityViolation", "check_scaffold_integrity"]
