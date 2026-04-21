"""Pre-backtest checks for agent-constructed strategy packages.

Two structural validators, both run before the validator agent spends
compute on a backtest:

- :mod:`checks.integrity` — catches template-scaffold leakage (unchanged
  template imports, wrong class names, mismatched ``MANIFEST.strategy_id``).
- :mod:`checks.manifest` — catches design-vs-engine mismatches (unknown
  ``DataRequirement`` kinds, orphaned signal columns, naive per-ticker
  groupby where a ``universe_returns`` panel is required, missing
  ``GrossExposureSizer`` wrap, ``ftc`` on a vectorized runner, attrs-wipe
  bugs).

Each produces a list of violation records with stable codes. An empty
list means the strategy passed; any record with ``severity == "error"``
(manifest) or any record at all (integrity) should block the backtest.

CLI entry points::

    python -m prophitai_algo_trading.checks.integrity <strategy_id>
    python -m prophitai_algo_trading.checks.manifest <strategy_id>
"""

from prophitai_algo_trading.checks.integrity import (
    IntegrityViolation,
    check_scaffold_integrity,
)
from prophitai_algo_trading.checks.manifest import (
    ManifestViolation,
    check_manifest_compatibility,
)

__all__ = [
    "IntegrityViolation",
    "ManifestViolation",
    "check_manifest_compatibility",
    "check_scaffold_integrity",
]
