"""Shared signal-model infrastructure."""

from prophitai_algo_trading.signals.base import BaseSignalModel, SignalDict
from prophitai_algo_trading.signals.primitives import (
    bars_since,
    cooldown_mask,
    cross_above,
    cross_below,
    debounce,
    fired_within,
    stays_above,
)

__all__ = [
    "BaseSignalModel",
    "SignalDict",
    "bars_since",
    "cooldown_mask",
    "cross_above",
    "cross_below",
    "debounce",
    "fired_within",
    "stays_above",
]
