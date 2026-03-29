"""ProphitAI Algo — algorithmic trading library.

Strategies, engines, indicators, execution, and broker interfaces.
Pure trading machinery with no agent or AI dependencies.
"""

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.strategies.macd_momentum import MACDMomentum
from prophitai_algo_trading.strategies.rsi_mean_reversion import RSIMeanReversion
from prophitai_algo_trading.strategies.ichimoku_cross import IchimokuCross
from prophitai_algo_trading.strategies.orb_breakout import ORBBreakout
from prophitai_algo_trading.strategies.squeeze_breakout import SqueezeBreakout
from prophitai_algo_trading.strategies.vwap_hurst_btc import VwapHurstBTC
from prophitai_algo_trading.strategies.kalman_stat_arb import KalmanStatArb
from prophitai_algo_trading.engines import LiveRunner, BacktestEngine, VectorizedBacktestEngine
from prophitai_algo_trading.broker import Alpaca
from prophitai_algo_trading.execution import (
    PortfolioTracker,
    PositionTracker,
    CostModel,
    InverseVolatilitySizer,
)

__all__ = [
    "BaseStrategy",
    "MACDMomentum",
    "RSIMeanReversion",
    "IchimokuCross",
    "ORBBreakout",
    "SqueezeBreakout",
    "VwapHurstBTC",
    "KalmanStatArb",
    "LiveRunner",
    "BacktestEngine",
    "VectorizedBacktestEngine",
    "Alpaca",
    "PortfolioTracker",
    "PositionTracker",
    "CostModel",
    "InverseVolatilitySizer",
]
