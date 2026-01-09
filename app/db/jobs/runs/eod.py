from app.db.jobs.market_data import UpdatePriceTable
from app.db.jobs.macro import (
    UpdateCommodityPrices,
    UpdateEconomicIndicators,
    UpdateEconomicCalendar,
    UpdateUSRates,
)
import time

def main():
    print("=" * 100)
    print("EOD DATA UPDATE JOB")
    print("=" * 100)

    update_price_table = UpdatePriceTable()

    # Capture final intraday prices (2pm-4pm gap)
    print("Updating final intraday prices...")
    update_price_table.update_all_ticker_prices(max_workers=2)

    time.sleep(60)

    # Update daily EOD prices
    print("Updating daily prices...")
    update_price_table.update_daily_prices(max_workers=2)
    
    time.sleep(60)
    
    # Update commodity prices
    print("Updating commodity prices...")
    commodity_updater = UpdateCommodityPrices()
    commodity_updater.update_all_commodities()
    
    time.sleep(60)
    
    # Update economic indicators
    print("Updating economic indicators...")
    indicator_updater = UpdateEconomicIndicators()
    indicator_updater.update_all_indicators()
    
    time.sleep(60)
    
    # Update economic calendar
    print("Updating economic calendar...")
    calendar_updater = UpdateEconomicCalendar()
    calendar_updater.update_with_summary()

    time.sleep(60)

    # Update US treasury rates
    print("Updating US treasury rates...")
    rates_updater = UpdateUSRates()
    rates_updater.update_with_summary()

    print("EOD data update completed!")

if __name__ == "__main__":
    main()