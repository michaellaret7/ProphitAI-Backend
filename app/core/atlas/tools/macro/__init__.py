"""Macro data tools for agents."""

from .commodities import (
    macro_commodities,
    MACRO_COMMODITIES_TOOL,
)
from .indicators import (
    macro_indicators,
    MACRO_INDICATORS_TOOL,
)
from .outlook import (
    get_outlook,
    MACRO_OUTLOOK_TOOL,
)
from .rates import (
    macro_rates,
    MACRO_RATES_TOOL,
)

__all__ = [
    # Functions
    "macro_commodities",
    "macro_indicators",
    "get_outlook",
    "macro_rates",
    # Tool definitions
    "MACRO_COMMODITIES_TOOL",
    "MACRO_INDICATORS_TOOL",
    "MACRO_OUTLOOK_TOOL",
    "MACRO_RATES_TOOL",
]
