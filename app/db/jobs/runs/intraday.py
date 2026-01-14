from app.db.jobs.market_data import UpdateTickerTable, UpdatePriceTable
from app.db.jobs.portfolio import UpdatePortfolios
import time
import sys
import traceback

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
    try:
        with UpdatePortfolios() as update_portfolio:
            update_portfolio.update_portfolios()
        print("Portfolio update completed successfully!")
    except Exception as e:
        print(f"ERROR in portfolio update: {type(e).__name__}: {e}")
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)

    print("Intraday update completed!")

if __name__ == "__main__":
    main()