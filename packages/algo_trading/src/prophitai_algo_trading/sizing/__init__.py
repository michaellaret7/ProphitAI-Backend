"""Position sizing policies.

Sizers receive a SizingInput (price, portfolio state, optional per-ticker
indicator snapshot) and return a share count. That's the whole contract.
"""

from prophitai_algo_trading.sizing.base import BaseSizer, SizingInput
from prophitai_algo_trading.sizing.equity import (
    AllInSizer,
    FixedQuantitySizer,
    PercentOfEquitySizer,
)
from prophitai_algo_trading.sizing.volatility import (
    InverseVolatilitySizer,
    VolatilityTargetSizer,
)
from prophitai_algo_trading.sizing.risk_based import ATRRiskSizer

__all__ = [
    "BaseSizer",
    "SizingInput",
    "AllInSizer",
    "FixedQuantitySizer",
    "PercentOfEquitySizer",
    "InverseVolatilitySizer",
    "VolatilityTargetSizer",
    "ATRRiskSizer",
]
