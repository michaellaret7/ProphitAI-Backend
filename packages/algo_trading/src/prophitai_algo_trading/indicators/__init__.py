"""Shared indicator building blocks and composition utilities."""

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_algo_trading.indicators.registry import INDICATOR_REGISTRY
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.indicators.pipeline import (
    BaseIndicatorSuite,
    IndicatorPipeline,
)
from prophitai_algo_trading.indicators.std_lib import (
    ADXIndicator,
    ATRIndicator,
    BollingerBandsIndicator,
    BollingerPctBIndicator,
    DonchianChannelsIndicator,
    ExponentialMovingAverageIndicator,
    MACDIndicator,
    OBVIndicator,
    RSI,
    RateOfChangeIndicator,
    SimpleMovingAverageIndicator,
    VWAPIndicator,
    ZScoreIndicator,
)

# ================================
# --> Registry registration
# ================================

INDICATOR_REGISTRY.register("sma", SimpleMovingAverageIndicator)
INDICATOR_REGISTRY.register("ema", ExponentialMovingAverageIndicator)
INDICATOR_REGISTRY.register("rsi", RSI)
INDICATOR_REGISTRY.register("macd", MACDIndicator)
INDICATOR_REGISTRY.register("adx", ADXIndicator)
INDICATOR_REGISTRY.register("roc", RateOfChangeIndicator)
INDICATOR_REGISTRY.register("atr", ATRIndicator)
INDICATOR_REGISTRY.register("bollinger_bands", BollingerBandsIndicator)
INDICATOR_REGISTRY.register("bollinger_pct_b", BollingerPctBIndicator)
INDICATOR_REGISTRY.register("donchian_channels", DonchianChannelsIndicator)
INDICATOR_REGISTRY.register("obv", OBVIndicator)
INDICATOR_REGISTRY.register("vwap", VWAPIndicator)
INDICATOR_REGISTRY.register("zscore", ZScoreIndicator)

__all__ = [
    "BaseIndicator",
    "BaseIndicatorSuite",
    "IndicatorPipeline",
    "IndicatorSpec",
    "INDICATOR_REGISTRY",
    "SimpleMovingAverageIndicator",
    "ExponentialMovingAverageIndicator",
    "RSI",
    "MACDIndicator",
    "ADXIndicator",
    "RateOfChangeIndicator",
    "ATRIndicator",
    "BollingerBandsIndicator",
    "BollingerPctBIndicator",
    "DonchianChannelsIndicator",
    "OBVIndicator",
    "VWAPIndicator",
    "ZScoreIndicator",
]
