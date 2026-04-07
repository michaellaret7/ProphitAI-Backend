"""
Backfill VIX data into the commodity_prices table.

Uses the existing UpdateCommodityPrices job to fetch 10 years of OHLCV
data from FMP and upsert into the macro database.
"""
from prophitai_data.jobs.macro.commodity_prices_update import UpdateCommodityPrices
from prophitai_data.repositories.macro import get_commodity_prices


def main():
    updater = UpdateCommodityPrices()

    print("Backfilling VIXUSD into commodity_prices...")
    records = updater.update_commodity("VIXUSD")
    print(f"\nInserted/updated {records} records.")

    # Verify
    df = get_commodity_prices("VIXUSD")
    print(f"\nVerification - rows in DB: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"\nSample data:")
    print(df.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
