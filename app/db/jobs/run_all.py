from app.db.jobs.fundamentals import FundamentalsUpdater
from app.db.jobs.portfolio import UpdatePortfolios
from app.db.jobs.market_data import UpdateTickerTable, UpdatePriceTable, is_after_market_close
from app.db.jobs.macro import (
    UpdateCommodityPrices,
    UpdateEconomicIndicators,
    UpdateEconomicCalendar,
)
from app.db.jobs.screeners import UpdateETFScreenerTable, UpdateEquityScreenerTable
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
    last_price_dict = update_price_table.create_last_price_dict()
    print(f"Found {len(last_price_dict)} tickers with price data\n")
    update_price_table.update_all_ticker_prices(max_workers=2)

    print("\nUpdating portfolio...\n")
    print("="*100)
    time.sleep(60)
    update_portfolio = UpdatePortfolios()
    update_portfolio.update_portfolios()
    update_portfolio.close()
    print("="*100)

    # If after market close (5PM EST), also update EOD prices and commodity data
    if is_after_market_close():
        print("\nMarket closed - updating EOD prices...")
        update_price_table.update_daily_prices(max_workers=2)

        time.sleep(60)

        print("\nMarket closed - updating commodity prices...")
        commodity_updater = UpdateCommodityPrices()
        commodity_updater.update_all_commodities()

        time.sleep(60)
        print("="*100)

        print("\nUpdating economic indicators...")
        indicator_updater = UpdateEconomicIndicators()
        indicator_updater.update_all_indicators()

        time.sleep(60)
        print("="*100)

        print("\nUpdating economic calendar...")
        calendar_updater = UpdateEconomicCalendar()
        calendar_updater.update_with_summary()

        print("="*100)
        time.sleep(60)

        print("\nUpdating ETF screener...")
        etf_updater = UpdateETFScreenerTable()
        etf_updater.run_update()

        time.sleep(60)
        print("\nUpdating equity screener...")
        equity_updater = UpdateEquityScreenerTable()
        equity_updater.run_update()

        time.sleep(60)
        print("="*100)
        


    print("\nAll updates completed successfully!\n")

if __name__ == "__main__":
    main()