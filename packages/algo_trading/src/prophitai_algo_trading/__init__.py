"""ProphitAI Algo Trading.

Composable algorithm framework for research -> backtest -> deploy.
Alpha -> PortfolioConstruction -> RiskManagement -> Execution is the
same pipeline in backtest and live; only the ``ExecutionModel``'s sink
differs (``PortfolioSink`` for backtest, ``BrokerSink`` for live).

Quick start::

    from prophitai_algo_trading import Algorithm, Backtest, CostModel
    from prophitai_algo_trading.alphas import MomentumAlpha, BreakoutAlpha
    from prophitai_algo_trading.portfolio_construction import (
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

from prophitai_algo_trading.brokers import Alpaca
from prophitai_algo_trading.accounting.cost_model import CostModel
from prophitai_algo_trading.data.csv_loader import load_csv_data
from prophitai_algo_trading.engines import (
    AlphaIsolationReport,
    Backtest,
    BarRunner,
    LiveRunner,
    VectorBacktest,
    run_alpha_isolation,
)
from prophitai_algo_trading.core.enums import Direction
from prophitai_algo_trading.core import (
    AlgorithmContext,
    AlphaModel,
    ExecutionModel,
    Insight,
    PortfolioConstructionModel,
    PortfolioTarget,
    PricePanel,
    RiskManagementModel,
    VectorAlgorithm,
    VectorAlpha,
    VectorPCM,
    panel_from_per_ticker,
)
from prophitai_algo_trading.core.algorithm import Algorithm
from prophitai_algo_trading.analytics.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.accounting.portfolio import Portfolio, Position, Trade

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
    # Vector framework
    "VectorAlgorithm",
    "VectorAlpha",
    "VectorPCM",
    "PricePanel",
    "panel_from_per_ticker",
    # Engines
    "AlphaIsolationReport",
    "Backtest",
    "BarRunner",
    "LiveRunner",
    "VectorBacktest",
    "run_alpha_isolation",
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
