"""Algorithm framework — Insight, PortfolioTarget, protocols, and Algorithm.

Phase 0 of the framework migration. Only the contract types live here.
Concrete implementations of AlphaModel, PortfolioConstructionModel,
RiskManagementModel, and ExecutionModel arrive in Phases 1-4.

See ``docs/algo_trading/framework.md`` for the full architecture decision.
"""

from prophitai_algo_trading.framework.algorithm import Algorithm
from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.protocols import (
    AlphaModel,
    ExecutionModel,
    PortfolioConstructionModel,
    RiskManagementModel,
)

__all__ = [
    "AlgorithmContext",
    "Insight",
    "PortfolioTarget",
    "AlphaModel",
    "ExecutionModel",
    "PortfolioConstructionModel",
    "RiskManagementModel",
    "Algorithm",
]
