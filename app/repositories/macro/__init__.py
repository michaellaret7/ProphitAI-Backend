"""Macro data repository package.

Provides access to commodity prices, government bond rates,
economic indicators, and economic calendar data.
"""

from app.repositories.macro.commodities import get_commodity_prices
from app.repositories.macro.rates import get_government_bond_rates
from app.repositories.macro.indicators import get_economic_indicators
from app.repositories.macro.calendar import get_economic_calendar

__all__ = [
    "get_commodity_prices",
    "get_government_bond_rates",
    "get_economic_indicators",
    "get_economic_calendar",
]
