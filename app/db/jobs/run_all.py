from app.db.jobs.fundamentals_table import UpdateFundamentalData
from app.db.jobs.ticker_table import UpdateTickerTable
from app.db.jobs.price_table import UpdatePriceTable
from app.db.jobs.macro_table import update_all_macro_data
import time

def main():
    print("Updating ticker table...")
    print("="*100)
    update_ticker_table = UpdateTickerTable()
    update_ticker_table.run_update_parallel(max_workers=2)

    # This is a 60 second pause (not minutes)
    time.sleep(60)
    print("="*100)

    print("\nUpdating price table...\n")
    print("="*100)
    update_price_table = UpdatePriceTable()
    # First show the current state
    last_price_dict = update_price_table.create_last_price_dict()
    print(f"Found {len(last_price_dict)} tickers with price data\n")
    update_price_table.update_all_ticker_prices(max_workers=2)

    time.sleep(60)
    print("="*100)

    print("\nUpdating macro data (commodities, economic indicators, calendar)...\n")
    print("="*100)
    results = update_all_macro_data()

    print("="*100)

    # print("\nUpdating fundamental data...\n")
    # print("="*100)
    # updater = UpdateFundamentalData()
    # # Uncomment to run full update
    # updater.update_all_fundamentals(max_workers=5) 

    # print("="*100)
    print("\nAll updates completed successfully!\n")

if __name__ == "__main__":
    main()