"""ProphitAI Algo Trading.

Research → backtest → deploy. Flat architecture, matrix-math vectorized
engine, honest event-driven engine, ZMQ-based live runner against Alpaca.
"""

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.enums import Direction
from prophitai_algo_trading.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.portfolio import Portfolio, Position, Trade
from prophitai_algo_trading.strategy import BaseStrategy

from prophitai_algo_trading.data.loader import load_csv_data
from prophitai_algo_trading.engines import (
    EventDrivenBacktest,
    LiveRunner,
    VectorizedBacktest,
)
from prophitai_algo_trading.broker import Alpaca

__all__ = [
    "BaseStrategy",
    "CostModel",
    "Direction",
    "BacktestResult",
    "calculate_metrics",
    "Portfolio",
    "Position",
    "Trade",
    "load_csv_data",
    "VectorizedBacktest",
    "EventDrivenBacktest",
    "LiveRunner",
    "Alpaca",
]
