"""Engines package — all strategy drivers (backtest, vectorized, live)."""

from prophitai_algo_trading.engines.backtest import (
    EventDrivenBacktestEngine,
    VectorizedBacktestEngine,
)

__all__ = [
    "EventDrivenBacktestEngine",
    "VectorizedBacktestEngine",
]

try:
    from prophitai_algo_trading.engines.live import LiveRunner
except ModuleNotFoundError:
    LiveRunner = None  # type: ignore[assignment]
else:
    __all__.append("LiveRunner")
