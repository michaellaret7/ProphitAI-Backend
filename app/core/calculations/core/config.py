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

__all__ = [
    "DEFAULT_TRADING_DAYS",
    "DEFAULT_RF_ANNUAL",
    "DEFAULT_CONFIDENCE",
    "DEFAULT_SECTOR_COL",
    "DEFAULT_WINSOR_LIMITS",
]


