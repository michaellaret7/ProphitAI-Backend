from app.db.jobs.ticker_table import UpdateTickerTable
from app.db.jobs.price_table import UpdatePriceTable
from app.db.jobs.portfolio import UpdatePortfolios
import time

def main():
    print("=" * 100)
    print("INTRADAY UPDATE JOB")
    print("=" * 100)
    
    # Update ticker metadata
    print("Updating ticker table...")
    update_ticker_table = UpdateTickerTable()
    update_ticker_table.run_update_parallel(max_workers=2)
    
    time.sleep(60)
    
    # Update intraday prices only
    print("Updating intraday prices...")
    update_price_table = UpdatePriceTable()
    update_price_table.update_all_ticker_prices(max_workers=2)

    time.sleep(60)

    print("Updating portfolios...")
    update_portfolio = UpdatePortfolios()
    update_portfolio.update_portfolios()
    update_portfolio.close()
    
    print("Intraday update completed!")

if __name__ == "__main__":
    main()