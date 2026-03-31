"""Shared indicator building blocks and composition utilities."""

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_algo_trading.indicators.registry import INDICATOR_REGISTRY
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.indicators.pipeline import (
    BaseIndicatorSuite,
    IndicatorPipeline,
)
from prophitai_algo_trading.indicators.moving_averages import (
    ExponentialMovingAverageIndicator,
    SimpleMovingAverageIndicator,
)
from prophitai_algo_trading.indicators.rsi import RSI

INDICATOR_REGISTRY.register("sma", SimpleMovingAverageIndicator)
INDICATOR_REGISTRY.register("ema", ExponentialMovingAverageIndicator)
INDICATOR_REGISTRY.register("rsi", RSI)

__all__ = [
    "BaseIndicator",
    "BaseIndicatorSuite",
    "IndicatorPipeline",
    "IndicatorSpec",
    "INDICATOR_REGISTRY",
    "SimpleMovingAverageIndicator",
    "ExponentialMovingAverageIndicator",
    "RSI",
]
