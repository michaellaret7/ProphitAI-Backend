"""ProphitAI Algo Trading.

Composable algorithm framework for research -> backtest -> deploy.
Alpha -> PortfolioConstruction -> RiskManagement -> Execution is the
same pipeline in backtest and live; only the ExecutionModel differs.

Quick start::

    from prophitai_algo_trading import Algorithm, EventDrivenBacktest, CostModel
    from prophitai_algo_trading.alphas import MomentumAlpha, BreakoutAlpha
    from prophitai_algo_trading.framework.portfolio_construction import (
        MagnitudeWeightedLongShortPCM,
        MultiAlphaBlendPCM,
    )
    from prophitai_algo_trading.risk import (
        CompositeRiskModel, MaxDrawdownRiskModel, MaxGrossExposureRiskModel,
    )
    from prophitai_algo_trading.framework.execution import SimulatedExecutionModel

    algo = Algorithm(
        alphas=[MomentumAlpha(), BreakoutAlpha()],
        portfolio_construction=MultiAlphaBlendPCM(
            weights={"momentum": 0.5, "breakout": 0.5},
            inner=MagnitudeWeightedLongShortPCM(gross_exposure=1.5),
        ),
        risk_management=CompositeRiskModel([
            MaxDrawdownRiskModel(max_drawdown_pct=0.15),
            MaxGrossExposureRiskModel(max_gross=1.5),
        ]),
        execution=SimulatedExecutionModel(min_change_pct=0.005),
    )

    result = EventDrivenBacktest(algo, initial_capital=1_000_000.0).run(data)
"""

from prophitai_algo_trading.broker import Alpaca
from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.data.loader import load_csv_data
from prophitai_algo_trading.engines import (
    EventDrivenBacktest,
    LiveRunner,
)
from prophitai_algo_trading.enums import Direction
from prophitai_algo_trading.framework import (
    AlgorithmContext,
    AlphaModel,
    ExecutionModel,
    Insight,
    PortfolioConstructionModel,
    PortfolioTarget,
    RiskManagementModel,
)
from prophitai_algo_trading.framework.algorithm import Algorithm
from prophitai_algo_trading.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.portfolio import Portfolio, Position, Trade

__all__ = [
    # Framework core
    "Algorithm",
    "AlgorithmContext",
    "Insight",
    "PortfolioTarget",
    "AlphaModel",
    "PortfolioConstructionModel",
    "RiskManagementModel",
    "ExecutionModel",
    # Engines
    "EventDrivenBacktest",
    "LiveRunner",
    # Portfolio / accounting
    "Portfolio",
    "Position",
    "Trade",
    "CostModel",
    # Enums + metrics
    "Direction",
    "BacktestResult",
    "calculate_metrics",
    # Data loading + broker
    "load_csv_data",
    "Alpaca",
]
