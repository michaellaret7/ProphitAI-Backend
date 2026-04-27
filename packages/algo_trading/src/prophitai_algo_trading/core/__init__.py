"""Core framework contracts — dataclasses, protocols, and the Algorithm composer.

Every pipeline stage (alpha → portfolio construction → risk → execution)
depends on the types defined here. No concrete stage implementations
live in this package — only the contracts.
"""

from prophitai_algo_trading.core.algorithm import Algorithm
from prophitai_algo_trading.core.enums import Direction
from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.core.panel import PricePanel, panel_from_per_ticker
from prophitai_algo_trading.core.protocols import (
    AlphaModel,
    ExecutionModel,
    LifecycleAwareRiskModel,
    PortfolioConstructionModel,
    RiskManagementModel,
    VectorAlpha,
    VectorPCM,
)
from prophitai_algo_trading.core.vector_algorithm import VectorAlgorithm

__all__ = [
    "Algorithm",
    "AlgorithmContext",
    "AlphaModel",
    "Direction",
    "ExecutionModel",
    "Insight",
    "LifecycleAwareRiskModel",
    "PortfolioConstructionModel",
    "PortfolioTarget",
    "PricePanel",
    "RiskManagementModel",
    "VectorAlgorithm",
    "VectorAlpha",
    "VectorPCM",
    "panel_from_per_ticker",
]
