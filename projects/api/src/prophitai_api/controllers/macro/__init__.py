"""Macro controllers — economic data, market data, and sector/industry data."""

from .economic import (
    get_commodity_prices_controller,
    get_bond_rates_controller,
    get_economic_indicator_controller,
    get_economic_calendar_controller,
)
from .market import (
    get_mergers_acquisitions_latest_controller,
    get_mergers_acquisitions_search_controller,
    get_fx_historical_prices_controller,
    get_index_list_controller,
)
from .sector import (
    get_sector_performance_controller,
    get_sector_pe_controller,
    get_industry_performance_controller,
    get_industry_pe_controller,
)

__all__ = [
    # economic
    "get_commodity_prices_controller",
    "get_bond_rates_controller",
    "get_economic_indicator_controller",
    "get_economic_calendar_controller",
    # market
    "get_mergers_acquisitions_latest_controller",
    "get_mergers_acquisitions_search_controller",
    "get_fx_historical_prices_controller",
    "get_index_list_controller",
    # sector
    "get_sector_performance_controller",
    "get_sector_pe_controller",
    "get_industry_performance_controller",
    "get_industry_pe_controller",
]
