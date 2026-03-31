"""ProphitAI Algo — algorithmic trading library.

Strategies, engines, indicators, execution, and broker interfaces.
Pure trading machinery with no agent or AI dependencies.
"""

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_algo_trading.engines import (
    EventDrivenBacktestEngine,
    VectorizedBacktestEngine,
)
from prophitai_algo_trading.indicators import (
    BaseIndicator,
    BaseIndicatorSuite,
    INDICATOR_REGISTRY,
    IndicatorPipeline,
    IndicatorSpec,
)
from prophitai_algo_trading.signals import BaseSignalModel
from prophitai_algo_trading.execution import (
    PortfolioContext,
    PortfolioTracker,
    PositionTracker,
    CostModel,
    EntryCandidate,
    SizingDecision,
)
from prophitai_algo_trading.sizing import (
    ATRRiskSizer,
    DrawdownScaledSizer,
    InverseVolatilitySizer,
    VolatilityTargetSizer,
)

try:
    from prophitai_algo_trading.engines import LiveRunner
except ModuleNotFoundError:
    LiveRunner = None  # type: ignore[assignment]

try:
    from prophitai_algo_trading.broker import Alpaca
except ModuleNotFoundError:
    Alpaca = None  # type: ignore[assignment]

__all__ = [
    "BaseStrategy",
    "BaseComposableStrategy",
    "EventDrivenBacktestEngine",
    "VectorizedBacktestEngine",
    "BaseIndicator",
    "BaseIndicatorSuite",
    "BaseSignalModel",
    "IndicatorPipeline",
    "IndicatorSpec",
    "INDICATOR_REGISTRY",
    "PortfolioContext",
    "PortfolioTracker",
    "PositionTracker",
    "CostModel",
    "SizingDecision",
    "EntryCandidate",
    "ATRRiskSizer",
    "DrawdownScaledSizer",
    "InverseVolatilitySizer",
    "VolatilityTargetSizer",
]

if LiveRunner is not None:
    __all__.append("LiveRunner")

if Alpaca is not None:
    __all__.append("Alpaca")
