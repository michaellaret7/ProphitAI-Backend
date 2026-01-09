"""
Market Data Update Package

This package contains updaters for market data:
- UpdateTickerTable: Updates ticker metadata from FMP API
- UpdatePriceTable: Updates intraday and daily price tables

Helper functions:
- is_after_market_close: Check if after 5PM EST
- get_current_est_time: Get current EST time
- run_price_updates: Run price updates based on time of day

Usage:
    from app.db.jobs.market_data import UpdateTickerTable, UpdatePriceTable

    # Update ticker metadata
    ticker_updater = UpdateTickerTable()
    ticker_updater.run_update_parallel(max_workers=5)

    # Update prices
    price_updater = UpdatePriceTable()
    price_updater.update_all_ticker_prices(max_workers=10)
"""

from app.db.jobs.market_data.ticker import UpdateTickerTable
from app.db.jobs.market_data.price import (
    UpdatePriceTable,
    is_after_market_close,
    get_current_est_time,
    run_price_updates,
)

__all__ = [
    'UpdateTickerTable',
    'UpdatePriceTable',
    'is_after_market_close',
    'get_current_est_time',
    'run_price_updates',
]
