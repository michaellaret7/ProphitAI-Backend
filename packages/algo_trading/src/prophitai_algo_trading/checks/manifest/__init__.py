"""Structural compatibility checks for agent-generated strategy packages.

Catches the design-vs-engine mismatches that silently produce zero-trade
backtests: unknown ``DataRequirement`` kinds, orphaned signal columns,
naive per-ticker groupby where a ``universe_returns`` panel is required,
missing ``GrossExposureSizer`` wrap, fixed-cost config on a vectorized
runner, and attrs-wipe bugs.

The full rule set and fix index live in
``documentation/framework_reference.md (Strategies repo)``.
"""

from prophitai_algo_trading.checks.manifest.checker import (
    check_manifest_compatibility,
)
from prophitai_algo_trading.checks.manifest.violations import ManifestViolation

__all__ = ["ManifestViolation", "check_manifest_compatibility"]
