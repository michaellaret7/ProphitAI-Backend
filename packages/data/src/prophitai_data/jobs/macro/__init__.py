"""
Macro Jobs Package

Contains individual updater modules for macro data.
"""

from prophitai_data.jobs.macro.commodity_prices_update import UpdateCommodityPrices
from prophitai_data.jobs.macro.economic_indicators_update import UpdateEconomicIndicators
from prophitai_data.jobs.macro.economic_calendar_update import UpdateEconomicCalendar
from prophitai_data.jobs.macro.us_rates_update import UpdateUSRates

__all__ = [
    'UpdateCommodityPrices',
    'UpdateEconomicIndicators',
    'UpdateEconomicCalendar',
    'UpdateUSRates',
]
