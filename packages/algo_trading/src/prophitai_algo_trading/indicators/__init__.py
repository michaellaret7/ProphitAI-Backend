"""Standard technical indicators as pure functions.

Every indicator takes a DataFrame, adds one or more columns, and returns it.
No classes, no warmup bookkeeping, no incremental updates — just calculate.
"""

from prophitai_algo_trading.indicators.momentum import (
    adx,
    macd,
    roc,
    rsi,
)
from prophitai_algo_trading.indicators.trend import ema, sma
from prophitai_algo_trading.indicators.volatility import (
    atr,
    bollinger,
    donchian,
    realized_vol,
)
from prophitai_algo_trading.indicators.statistical import rolling_max, zscore
from prophitai_algo_trading.indicators.volume import obv, vwap

__all__ = [
    "adx", "macd", "roc", "rsi",
    "ema", "sma",
    "atr", "bollinger", "donchian", "realized_vol",
    "rolling_max", "zscore",
    "obv", "vwap",
]
