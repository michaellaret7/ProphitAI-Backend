"""Shared configuration constants for calculations_v2.

These values are imported by helpers/factors/performance/risk modules to avoid
hardcoding the same literals across files.
"""

from __future__ import annotations

# Calendar and compounding
DEFAULT_TRADING_DAYS: int = 252

# Risk-free and confidence defaults
DEFAULT_RF_ANNUAL: float = 0.04
DEFAULT_CONFIDENCE: float = 0.99

# Cross-sectional defaults
DEFAULT_SECTOR_COL: str = "sector"
DEFAULT_WINSOR_LIMITS: tuple[float, float] = (0.025, 0.025)

# Standard lookback periods (in calendar days for use with timedelta)
DEFAULT_LOOKBACK_1Y: int = 365     # 1 year
DEFAULT_LOOKBACK_2Y: int = 730     # 2 years
DEFAULT_LOOKBACK_3Y: int = 1095    # 3 years

__all__ = [
    "DEFAULT_TRADING_DAYS",
    "DEFAULT_RF_ANNUAL",
    "DEFAULT_CONFIDENCE",
    "DEFAULT_SECTOR_COL",
    "DEFAULT_WINSOR_LIMITS",
    "DEFAULT_LOOKBACK_1Y",
    "DEFAULT_LOOKBACK_2Y",
    "DEFAULT_LOOKBACK_3Y",
]


