"""Data access layer — clients, repositories, streaming, and data resolution."""

from prophitai_algo_trading.data.load import load_backtest_data
from prophitai_algo_trading.data.preflight import (
    CoverageFailure,
    DataCoverageError,
    preflight_check,
)
from prophitai_algo_trading.data.resolver import (
    BaseDataProvider,
    DataResolver,
    build_default_resolver,
    load_strategy_data,
)

__all__ = [
    "BaseDataProvider",
    "CoverageFailure",
    "DataCoverageError",
    "DataResolver",
    "build_default_resolver",
    "load_backtest_data",
    "load_strategy_data",
    "preflight_check",
]
