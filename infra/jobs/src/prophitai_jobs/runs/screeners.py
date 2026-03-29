from prophitai_jobs.screeners import UpdateETFScreenerTable, UpdateEquityScreenerTable
import time

def main():
    print("=" * 100)
    print("SCREENER UPDATE JOB")
    print("=" * 100)
    
    # Update ETF screener (faster, ~10-30 min)
    print("Updating ETF screener...")
    etf_updater = UpdateETFScreenerTable()
    etf_updater.run_update()
    
    time.sleep(60)
    
    # Update equity screener (slower, ~1-3 hours)
    print("Updating equity screener...")
    equity_updater = UpdateEquityScreenerTable()
    equity_updater.run_update()
    
    print("Screener update completed!")

if __name__ == "__main__":
    main()