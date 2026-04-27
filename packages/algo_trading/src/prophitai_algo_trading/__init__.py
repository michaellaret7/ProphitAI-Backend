"""ProphitAI Algo Trading.

Composable algorithm framework for research -> backtest -> deploy.
Alpha -> PortfolioConstruction -> RiskManagement -> Execution is the
same pipeline in backtest and live; only the ``ExecutionModel``'s sink
differs (``PortfolioSink`` for backtest, ``BrokerSink`` for live).

Quick start::

    from prophitai_algo_trading import Algorithm, Backtest, CostModel
    from prophitai_algo_trading.alpha_signals import MomentumAlpha, BreakoutAlpha
    from prophitai_algo_trading.construction import (
        MagnitudeWeightedLongShortPCM,
        MultiAlphaBlendPCM,
    )
    from prophitai_algo_trading.risk import (
        CompositeRiskModel, MaxDrawdownRiskModel, MaxGrossExposureRiskModel,
    )
    from prophitai_algo_trading.execution import (
        ExecutionModel, PortfolioSink,
    )

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
        execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
    )

    result = Backtest(algo, initial_capital=1_000_000.0).run(data)
"""

from prophitai_algo_trading.algorithm import Algorithm, VectorAlgorithm
from prophitai_algo_trading.analytics import (
    AlphaIsolationReport,
    BacktestResult,
    calculate_metrics,
    run_alpha_isolation,
)
from prophitai_algo_trading.brokers import Alpaca
from prophitai_algo_trading.core import (
    AlgorithmContext,
    AlphaModel,
    Direction,
    ExecutionModel,
    Insight,
    PortfolioConstructionModel,
    PortfolioTarget,
    PricePanel,
    RiskManagementModel,
    VectorAlpha,
    VectorPCM,
    panel_from_per_ticker,
)
from prophitai_algo_trading.data import load_csv_data
from prophitai_algo_trading.engines import (
    Backtest,
    BarRunner,
    LiveRunner,
    VectorBacktest,
)
from prophitai_algo_trading.portfolio import (
    CostModel,
    Portfolio,
    Position,
    Trade,
)

__all__ = [
    # Strategy composers
    "Algorithm",
    "VectorAlgorithm",
    # Stage protocols
    "AlphaModel",
    "PortfolioConstructionModel",
    "RiskManagementModel",
    "ExecutionModel",
    "VectorAlpha",
    "VectorPCM",
    # Shared dataclasses + types
    "AlgorithmContext",
    "Insight",
    "PortfolioTarget",
    "PricePanel",
    "panel_from_per_ticker",
    "Direction",
    # Engines
    "Backtest",
    "BarRunner",
    "LiveRunner",
    "VectorBacktest",
    # Analytics
    "AlphaIsolationReport",
    "BacktestResult",
    "calculate_metrics",
    "run_alpha_isolation",
    # Portfolio state
    "Portfolio",
    "Position",
    "Trade",
    "CostModel",
    # Data loading + broker
    "load_csv_data",
    "Alpaca",
]
