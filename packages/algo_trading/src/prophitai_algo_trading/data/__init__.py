"""Data access layer — clients, repositories, streaming, and data resolution."""

from prophitai_algo_trading.data.resolver import (
    BaseDataProvider,
    DataResolver,
    build_default_resolver,
    load_strategy_data,
)

__all__ = [
    "BaseDataProvider",
    "DataResolver",
    "build_default_resolver",
    "load_strategy_data",
]
