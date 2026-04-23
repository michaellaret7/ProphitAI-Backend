"""Built-in ExecutionModels — PortfolioTargets to orders.

Two primitives covering the backtest/live split:

    SimulatedExecutionModel   in-memory portfolio mutation (backtest)
    BrokerExecutionModel      Alpaca (or any buy/sell/close_position broker) + mirror

Both satisfy the ``ExecutionModel`` protocol. Phase 5's engine rewire
swaps these at the ``Algorithm`` boundary — everything above execution
(alphas, PCM, risk) is identical between backtest and live.
"""

from prophitai_algo_trading.framework.execution.broker import (
    BrokerExecutionModel,
)
from prophitai_algo_trading.framework.execution.simulated import (
    SimulatedExecutionModel,
)

__all__ = [
    "BrokerExecutionModel",
    "SimulatedExecutionModel",
]
