"""
Update Commodity Prices Table

This script updates the commodity_prices table with the latest data from FMP API.
It finds the last date for each commodity in the database and fetches new data
from that date to the current date, ensuring no duplicates are created.
"""
import os
import requests
from datetime import datetime, timedelta, date
from uuid import uuid5, NAMESPACE_DNS
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from dotenv import load_dotenv

from app.db.core.db_config import MacroDataSession
from app.db.core.models.macro_data_models import CommodityPrices
from app.utils.time_utils import get_current_utc_time

load_dotenv()


class UpdateCommodityPrices:
    """Updates commodity price data from FMP API"""

    # All available commodities from FMP API
    COMMODITIES = [
        'ALIUSD',   # Aluminum
        'BZUSD',    # Brent Crude Oil
        'CCUSD',    # Cocoa
        'CLUSD',    # Crude Oil (WTI)
        'CTUSX',    # Cotton #2
        'DXUSD',    # U.S. Dollar Index (DXY)
        'GCUSD',    # Gold
        'GFUSX',    # Feeder Cattle
        'HEUSX',    # Lean Hogs
        'HGUSD',    # Copper
        'HOUSD',    # Heating Oil
        'KCUSX',    # Coffee (Arabica)
        'KEUSX',    # Kansas City Wheat
        'LBUSD',    # Lumber
        'LEUSX',    # Live Cattle
        'NGUSD',    # Natural Gas
        'OJUSX',    # Orange Juice
        'PAUSD',    # Palladium
        'PLUSD',    # Platinum
        'RBUSD',    # RBOB Gasoline
        'SBUSX',    # Sugar #11
        'SILUSD',   # Physical Silver Index
        'SIUSD',    # Silver
        'YMUSD',    # Dow Jones (Mini) Index
        'ZCUSX',    # Corn
        'ZLUSX',    # Soybean Oil
        'ZMUSD',    # Soybean Meal
        'ZNUSD',    # U.S. 10-Year Treasury Note Futures
        'ZQUSD',    # 30-Day Fed Funds Futures
        'ZSUSX',    # Soybeans
    ]

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable not found")

        # Progress tracking
        self.total_commodities = 0
        self.processed = 0
        self.errors = 0
        self.total_records_added = 0

    @staticmethod
    def get_symbol_uuid(symbol: str):
        """
        Generate a deterministic UUID for a commodity symbol.
        Same symbol always gets the same UUID.

        Args:
            symbol: Commodity symbol (e.g., 'GCUSD')

        Returns:
            UUID for the symbol
        """
        return uuid5(NAMESPACE_DNS, f"commodity.{symbol}")

    def get_last_date_in_db(self, session, symbol: str) -> date | None:
        """
        Find the last date available in the database for a given commodity.

        Args:
            session: Database session
            symbol: Commodity symbol

        Returns:
            Last date in database, or None if no data exists
        """
        try:
            result = session.query(
                func.max(CommodityPrices.date)
            ).filter(
                CommodityPrices.symbol == symbol
            ).scalar()

            return result
        except Exception as e:
            print(f"Error getting last date for {symbol}: {e}")
            return None

    def fetch_commodity_data_from_api(
        self,
        symbol: str,
        from_date: str,
        to_date: str
    ) -> list[dict]:
        """
        Fetch commodity OHLCV data from FMP API.

        Args:
            symbol: Commodity symbol
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format

        Returns:
            List of dictionaries containing OHLCV data
        """
        base_url = "https://financialmodelingprep.com/api/v3"
        url = f"{base_url}/historical-price-full/{symbol}"

        params = {
            'apikey': self.api_key,
            'from': from_date,
            'to': to_date
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # FMP returns data in format: {'symbol': 'GCUSD', 'historical': [...]}
            if 'historical' in data and data['historical']:
                return data['historical']
            else:
                print(f"No data returned for {symbol} from {from_date} to {to_date}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"API request failed for {symbol}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching {symbol}: {e}")
            return []

    def update_commodity(self, symbol: str) -> int:
        """
        Update a single commodity with latest data.

        Args:
            symbol: Commodity symbol to update

        Returns:
            Number of records inserted/updated
        """
        session = MacroDataSession()

        try:
            # Get the last date in database
            last_date = self.get_last_date_in_db(session, symbol)

            # Determine the date range for fetching
            if last_date:
                # Start from the day after the last date
                start_date = last_date + timedelta(days=1)
            else:
                # No data exists, fetch from a reasonable historical date
                # Fetch last 10 years of data for new commodities
                start_date = get_current_utc_time().date() - timedelta(days=365 * 10)

            # End date is current UTC date
            end_date = get_current_utc_time().date()

            # Check if we need to fetch data
            if start_date > end_date:
                print(f"{symbol}: Already up to date (last date: {last_date})")
                return 0

            print(f"{symbol}: Fetching data from {start_date} to {end_date}")

            # Fetch data from API
            historical_data = self.fetch_commodity_data_from_api(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if not historical_data:
                print(f"{symbol}: No new data available")
                return 0

            # Prepare records for insertion
            symbol_uuid = self.get_symbol_uuid(symbol)
            current_time = get_current_utc_time()

            records = []
            for item in historical_data:
                # Parse date from the API response
                item_date = datetime.strptime(item['date'], '%Y-%m-%d').date()

                records.append({
                    'id': symbol_uuid,
                    'symbol': symbol,
                    'date': item_date,
                    'open': float(item['open']) if item.get('open') is not None else None,
                    'high': float(item['high']) if item.get('high') is not None else None,
                    'low': float(item['low']) if item.get('low') is not None else None,
                    'close': float(item['close']) if item.get('close') is not None else None,
                    'volume': float(item['volume']) if item.get('volume') is not None else None,
                    'created_at': current_time,
                    'updated_at': current_time
                })

            # Insert with upsert logic (on conflict, update)
            if records:
                stmt = insert(CommodityPrices).values(records)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_commodity_symbol_date',
                    set_={
                        'open': stmt.excluded.open,
                        'high': stmt.excluded.high,
                        'low': stmt.excluded.low,
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                        'updated_at': current_time
                    }
                )

                session.execute(stmt)
                session.commit()

                print(f"{symbol}: Successfully inserted/updated {len(records)} records")
                return len(records)

            return 0

        except Exception as e:
            session.rollback()
            print(f"{symbol}: Error during update - {e}")
            raise
        finally:
            session.close()

    def update_all_commodities(self):
        """
        Update all commodities in the COMMODITIES list.

        Returns:
            Dictionary with summary statistics
        """
        self.total_commodities = len(self.COMMODITIES)
        self.processed = 0
        self.errors = 0
        self.total_records_added = 0

        print(f"Starting commodity price update for {self.total_commodities} commodities...")
        print("=" * 70)

        results = {}

        for symbol in self.COMMODITIES:
            try:
                records_added = self.update_commodity(symbol)
                results[symbol] = {
                    'success': True,
                    'records_added': records_added
                }
                self.total_records_added += records_added
                self.processed += 1

            except Exception as e:
                print(f"{symbol}: FAILED - {e}")
                results[symbol] = {
                    'success': False,
                    'error': str(e)
                }
                self.errors += 1
                self.processed += 1

        # Print summary
        self._print_summary(results)

        return results

    def _print_summary(self, results: dict):
        """Print summary of the update process"""
        successful = sum(1 for r in results.values() if r['success'])

        print("\n" + "=" * 70)
        print("COMMODITY PRICE UPDATE SUMMARY")
        print("=" * 70)
        print(f"Total commodities: {self.total_commodities}")
        print(f"Successfully updated: {successful}")
        print(f"Failed: {self.errors}")
        print(f"Total records inserted/updated: {self.total_records_added:,}")
        print("=" * 70)

        # Show details for failed commodities
        if self.errors > 0:
            print("\nFailed commodities:")
            for symbol, result in results.items():
                if not result['success']:
                    print(f"  {symbol}: {result.get('error', 'Unknown error')}")
            print("=" * 70)


def main():
    """Main entry point for the script"""
    try:
        updater = UpdateCommodityPrices()
        results = updater.update_all_commodities()
        return results
    except Exception as e:
        print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
