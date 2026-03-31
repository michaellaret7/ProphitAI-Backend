"""Engines package — all strategy drivers (backtest, vectorized, live)."""

from prophitai_algo_trading.engines.backtest import BacktestEngine, VectorizedBacktestEngine

__all__ = [
    "BacktestEngine",
    "VectorizedBacktestEngine",
]

try:
    from prophitai_algo_trading.engines.live import LiveRunner
except ModuleNotFoundError:
    LiveRunner = None  # type: ignore[assignment]
else:
    __all__.append("LiveRunner")
