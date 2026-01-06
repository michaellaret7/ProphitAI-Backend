from app.db.jobs.price_table import UpdatePriceTable
from app.db.jobs.macro_jobs.commodity_prices_update import UpdateCommodityPrices
from app.db.jobs.macro_jobs.economic_indicators_update import UpdateEconomicIndicators
from app.db.jobs.macro_jobs.economic_calendar_update import UpdateEconomicCalendar
import time

def main():
    print("=" * 100)
    print("EOD DATA UPDATE JOB")
    print("=" * 100)
    
    # Update daily EOD prices
    print("Updating daily prices...")
    update_price_table = UpdatePriceTable()
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
    
    print("EOD data update completed!")

if __name__ == "__main__":
    main()