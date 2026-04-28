"""Core framework contracts — protocols, dataclasses, enums, and shared types.

Every pipeline stage (alpha → portfolio construction → risk → execution)
depends on the types defined here. No concrete stage implementations
or composers live in this package — only the contracts.

Concrete strategy composers live in ``algorithm/``.
"""

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
    PortfolioConstructor,
    RiskManagementModel,
    SignalBlender,
    VectorAlpha,
    VectorPortfolioConstructor,
    VectorSignalBlender,
)

__all__ = [
    "AlgorithmContext",
    "AlphaModel",
    "Direction",
    "ExecutionModel",
    "Insight",
    "LifecycleAwareRiskModel",
    "PortfolioConstructor",
    "PortfolioTarget",
    "PricePanel",
    "RiskManagementModel",
    "SignalBlender",
    "VectorAlpha",
    "VectorPortfolioConstructor",
    "VectorSignalBlender",
    "panel_from_per_ticker",
]
