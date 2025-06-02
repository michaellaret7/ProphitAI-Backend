"""
Portfolio-optimization umbrella package.

This subpackage contains two logical stages:
  • phase_one  - initial portfolio construction using LLMs
  • phase_two  - ticker selection, fundamental analysis, back-testing

Public helper functions are re-exported for convenience so callers only need

    from src.portfolio_optimization import optimize, pick_top_tickers, recommend

Legacy code may still import the previous module paths (``backend.src.portfolio_optimization.phase_one`` or
``backend.src.portfolio_optimization.phase_two``).  A lightweight shim registers these dotted names in
``sys.modules`` so they continue to resolve without code changes elsewhere.
"""

from __future__ import annotations

import importlib
import sys

# ---------------------------------------------------------------------------
# Re-export phase-specific public API
# ---------------------------------------------------------------------------

from .phase_one.phase_one_run import optimize  # noqa: F401
from .phase_two.phase_two_run import (
    pick_top_tickers_from_asset_classes as pick_top_tickers,
    make_phaseTwo_recommendations as recommend,
    run_phase_two,
)  # noqa: F401

__all__ = [
    "optimize",
    "pick_top_tickers",
    "recommend",
    "run_phase_two",
]

# ---------------------------------------------------------------------------
# Backwards-compatibility shims
# ---------------------------------------------------------------------------

# Map old top-level package names -> new modules so `import src.phaseOne...` keeps
# working until every call-site is updated.

_phase_one_pkg = importlib.import_module("backend.src.portfolio_optimization.phase_one")
_phase_two_pkg = importlib.import_module("backend.src.portfolio_optimization.phase_two")

sys.modules.setdefault("src.phaseOne", _phase_one_pkg)
sys.modules.setdefault("src.phaseTwo", _phase_two_pkg)

# Fine-grained sub-modules commonly imported directly
sys.modules.setdefault(
    "src.phaseTwo.data_retrieval",
    importlib.import_module("backend.src.portfolio_optimization.phase_two.data_retrieval"),
)
sys.modules.setdefault(
    "src.phaseTwo.phaseTwoCalculations",
    importlib.import_module("backend.src.portfolio_optimization.phase_two.phase_two_calculations"),
)
sys.modules.setdefault(
    "src.phaseTwo.retrieve_fundamental_report",
    importlib.import_module("backend.src.portfolio_optimization.phase_two.retrieve_fundamental_report"),
)
sys.modules.setdefault(
    "src.phaseTwo.phaseTwo",
    importlib.import_module("backend.src.portfolio_optimization.phase_two.phase_two_run"),
)
sys.modules.setdefault(
    "src.phaseTwo.backtest",
    importlib.import_module("backend.src.backtest.backtest_run"),
)
sys.modules.setdefault(
    "src.phaseTwo.phaseTwoBacktest",
    importlib.import_module("backend.src.backtest.backtest_run"),
)
sys.modules.setdefault(
    "src.phaseTwoBacktest",
    importlib.import_module("backend.src.backtest.backtest_run"),
)