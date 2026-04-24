"""Deep ``ExecutionModel`` + its ``OrderSink`` adapters.

One ``ExecutionModel`` class holds the full decision matrix
(flat / open / close / resize / flip + material-change filter + warmup
suppression). Its sink is the only thing that differs between backtest
and live:

    PortfolioSink   in-memory portfolio mutation (backtest)
    BrokerSink      Alpaca-shaped broker + mirror update (live)

Usage:

    Algorithm(..., execution=ExecutionModel(sink=PortfolioSink()))
    Algorithm(..., execution=ExecutionModel(sink=BrokerSink(alpaca)))
"""

from prophitai_algo_trading.execution.model import ExecutionModel
from prophitai_algo_trading.execution.sinks import (
    BrokerSink,
    OrderSink,
    PortfolioSink,
)

__all__ = [
    "BrokerSink",
    "ExecutionModel",
    "OrderSink",
    "PortfolioSink",
]
