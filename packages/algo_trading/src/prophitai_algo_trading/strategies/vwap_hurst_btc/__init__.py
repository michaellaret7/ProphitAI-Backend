"""VWAP Reversion + Hurst Regime strategy for 1-minute BTC.

Combines rolling VWAP reversion with Hurst exponent regime detection.
Trades mean-reversion when anti-persistent, momentum when persistent,
and stays flat during random-walk regimes.
"""

from prophitai_algo_trading.strategies.vwap_hurst_btc.strategy import VwapHurstBTC
from prophitai_algo_trading.strategies.vwap_hurst_btc.signals import (
    vwap_oversold,
    vwap_overbought,
    vwap_reverted_from_below,
    vwap_reverted_from_above,
    ema_bullish_cross,
    ema_bearish_cross,
    ema_fast_above_slow,
    ema_fast_below_slow,
    regime_mean_reverting,
    regime_trending,
    regime_random_walk,
)
from prophitai_algo_trading.strategies.vwap_hurst_btc.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

__all__ = [
    "VwapHurstBTC",
    "vwap_oversold",
    "vwap_overbought",
    "vwap_reverted_from_below",
    "vwap_reverted_from_above",
    "ema_bullish_cross",
    "ema_bearish_cross",
    "ema_fast_above_slow",
    "ema_fast_below_slow",
    "regime_mean_reverting",
    "regime_trending",
    "regime_random_walk",
    "long_entry",
    "long_exit",
    "short_entry",
    "short_exit",
]
