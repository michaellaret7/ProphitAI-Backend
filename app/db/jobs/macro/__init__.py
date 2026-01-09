"""
Macro Data Update Package

This package provides a cleaner import path for macro data updaters.
Re-exports updaters from macro_jobs/ for backwards compatibility.

Updaters:
- UpdateCommodityPrices: Updates commodity price data
- UpdateEconomicIndicators: Updates economic indicator data
- UpdateEconomicCalendar: Updates economic calendar events
- UpdateUSRates: Updates US Treasury rates

Usage:
    from app.db.jobs.macro import (
        UpdateCommodityPrices,
        UpdateEconomicIndicators,
        UpdateEconomicCalendar,
        UpdateUSRates,
    )

    # Update commodity prices
    commodity_updater = UpdateCommodityPrices()
    commodity_updater.update_all_commodities()
"""

from app.db.jobs.macro_jobs.commodity_prices_update import UpdateCommodityPrices
from app.db.jobs.macro_jobs.economic_indicators_update import UpdateEconomicIndicators
from app.db.jobs.macro_jobs.economic_calendar_update import UpdateEconomicCalendar
from app.db.jobs.macro_jobs.us_rates_update import UpdateUSRates

__all__ = [
    'UpdateCommodityPrices',
    'UpdateEconomicIndicators',
    'UpdateEconomicCalendar',
    'UpdateUSRates',
]
