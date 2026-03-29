from prophitai_data.jobs.fundamentals import FundamentalsUpdater

def main():
    print("=" * 100)
    print("END OF WEEK FUNDAMENTAL DATA UPDATE JOB")
    print("=" * 100)

    # Update all fundamental data (balance sheets, cash flows, income statements,
    # financial ratios, analyst estimates, ETF data, dividends, news, grades, etc.)
    print("Updating fundamental data for all tickers...")
    updater = FundamentalsUpdater()
    updater.update_all_fundamentals(max_workers=3)

    print("End of week fundamental data update completed!")

if __name__ == "__main__":
    main()
