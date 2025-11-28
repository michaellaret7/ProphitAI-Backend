"""
Price Table Update Jobs

This module handles updating two price tables in the market_data database:

1. Price (15-min intraday) - Updated at 10AM, 12PM, 2PM, and 5PM EST
2. DailyPrices (daily OHLCV) - Updated at 5PM EST only

Schedule:
- 10AM EST: Update intraday prices
- 12PM EST: Update intraday prices
- 2PM EST: Update intraday prices
- 5PM EST: Update intraday prices + daily prices
"""

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, Price, DailyPrices
from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta, timezone, time as dt_time
import time
from app.utils.time_utils import get_current_utc_time
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class UpdatePriceTable():
    def __init__(self):
        self.fmp_api = FMP_API_DATA()
        self.lock = threading.Lock()
        self.total_records = 0
        self.successful_updates = 0
        self.errors = 0
        self.processed = 0

    def create_last_price_dict(self):
        market_session = MarketSession()
        
        results = market_session.query(
            Price.ticker_id,
            func.max(Price.datetime).label('last_date')
        ).group_by(Price.ticker_id).all()
        
        # Convert to dictionary with ticker_id as key and last_date as value
        dict = {str(row.ticker_id): row.last_date for row in results}
        
        market_session.close()
        return dict

    def update_prices_for_single_ticker(self, ticker_id: str, last_date: datetime):
        """Update prices for a single ticker from last_date to current time"""
        market_session = MarketSession()
        try:
            # Get ticker symbol from ticker_id
            ticker = market_session.query(Ticker).filter(Ticker.id == ticker_id).first()
            if not ticker:
                print(f"Ticker not found for ID: {ticker_id}")
                return 0
            
            # Calculate date range (add 15 minutes to last_date to avoid duplicates)
            from_date = last_date + timedelta(minutes=15)
            to_date = get_current_utc_time()
            
            # Skip if data is already current (within 15 minutes)
            if (to_date - last_date).total_seconds() < 900:  # 900 seconds = 15 minutes
                return 0
            
            # Fetch data from FMP API
            price_data = self.fmp_api.get_intraday_prices_for_ticker(
                ticker.ticker, 
                from_date, 
                to_date
            )
            
            if not price_data:
                return 0
            
            # Bulk insert new price records
            records_inserted = self._bulk_insert_prices(market_session, ticker_id, price_data)
            market_session.commit()
            
            return records_inserted
            
        except Exception as e:
            print(f"Error updating ticker {ticker_id}: {str(e)}")
            market_session.rollback()
            return -1
        finally:
            market_session.close()
    
    def _bulk_insert_prices(self, session, ticker_id: str, price_data: list):
        """Convert FMP API response to Price records and bulk insert"""
        if not price_data:
            return 0

        # Set up timezone objects
        est = pytz.timezone('US/Eastern')

        # Convert FMP data to Price model format
        price_records = []
        for record in price_data:
            # FMP returns data like: {"date": "2024-01-01 09:30:00", "open": 100.0, ...}
            # Skip records without required date field
            if not record.get('date'):
                continue

            # Parse the datetime and localize to EST
            dt = datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S')
            dt_est = est.localize(dt)
            # Convert to UTC
            dt_utc = dt_est.astimezone(timezone.utc)

            price_records.append({
                'ticker_id': ticker_id,
                'datetime': dt_utc.replace(tzinfo=None),  # Remove timezone info for storage
                'open': record.get('open'),
                'high': record.get('high'),
                'low': record.get('low'),
                'close': record.get('close'),
                'volume': record.get('volume')
            })
        
        # Use PostgreSQL's ON CONFLICT to handle duplicates
        stmt = insert(Price).values(price_records)
        stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'datetime'])
        
        result = session.execute(stmt)
        return result.rowcount
    
    def _update_ticker_thread_safe(self, ticker_id: str, last_date: datetime):
        """Thread-safe wrapper for updating a single ticker"""
        records_inserted = self.update_prices_for_single_ticker(ticker_id, last_date)
        
        with self.lock:
            self.processed += 1
            if records_inserted > 0:
                self.successful_updates += 1
                self.total_records += records_inserted
            elif records_inserted == -1:
                self.errors += 1
            
            # Progress reporting every 50 tickers
            if self.processed % 50 == 0:
                print(f"Progress: {self.processed}/{self.total_tickers} tickers processed")
        
        return ticker_id, records_inserted
    
    def update_all_ticker_prices(self, max_workers=10):
        """Update prices for all tickers using thread pooling"""
        # Get the last price dictionary
        last_price_dict = self.create_last_price_dict()
        
        if not last_price_dict:
            print("No tickers found with price data")
            return
        
        # Reset counters
        self.total_tickers = len(last_price_dict)
        self.total_records = 0
        self.successful_updates = 0
        self.errors = 0
        self.processed = 0
        
        print(f"Updating prices for {self.total_tickers} tickers using {max_workers} threads...")
        start_time = time.time()
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self._update_ticker_thread_safe, ticker_id, last_date): ticker_id
                for ticker_id, last_date in last_price_dict.items()
            }
            
            # Process completed futures
            for future in as_completed(futures):
                try:
                    ticker_id, records = future.result()
                except Exception as e:
                    print(f"Error processing ticker: {e}")
                    with self.lock:
                        self.errors += 1
        
        # Final summary
        elapsed_time = time.time() - start_time
        print(f"\n{'='*50}")
        print("UPDATE COMPLETE!")
        print(f"{'='*50}")
        print(f"Total tickers processed: {self.total_tickers}")
        print(f"Successful updates: {self.successful_updates}")
        print(f"Total records inserted: {self.total_records}")
        print(f"Errors: {self.errors}")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        print(f"Average time per ticker: {elapsed_time/self.total_tickers:.2f} seconds")

    def update_daily_prices(self, max_workers=10):
        """Update the DailyPrices table with daily OHLCV data for all tickers.

        For each ticker, finds the last date in DailyPrices and fetches daily data
        from that date to today. Skips duplicates (on_conflict_do_nothing).

        This method should be called at 5PM EST after market close.
        """
        print(f"\n{'='*50}")
        print("UPDATING DAILY PRICES TABLE")
        print(f"{'='*50}")

        # Get all tickers
        session = MarketSession()
        tickers = session.query(Ticker).all()
        session.close()

        if not tickers:
            print("No tickers found")
            return

        # Reset counters
        self.total_tickers = len(tickers)
        self.total_records = 0
        self.successful_updates = 0
        self.errors = 0
        self.processed = 0

        print(f"Updating daily prices for {self.total_tickers} tickers using {max_workers} threads...")
        start_time = time.time()

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._update_daily_prices_for_ticker, ticker): ticker.ticker
                for ticker in tickers
            }

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    ticker_symbol = futures[future]
                    print(f"Error processing daily prices for {ticker_symbol}: {e}")
                    with self.lock:
                        self.errors += 1

        # Final summary
        elapsed_time = time.time() - start_time
        print(f"\n{'='*50}")
        print("DAILY PRICES UPDATE COMPLETE!")
        print(f"{'='*50}")
        print(f"Total tickers processed: {self.total_tickers}")
        print(f"Successful updates: {self.successful_updates}")
        print(f"Total daily records inserted: {self.total_records}")
        print(f"Errors: {self.errors}")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")

    def _update_daily_prices_for_ticker(self, ticker: Ticker):
        """Update daily prices for a single ticker (thread-safe).

        Finds the last date in DailyPrices and fetches daily data from that date to today,
        inserting new rows and skipping duplicates.
        """
        session = MarketSession()
        try:
            # Find the last date in DailyPrices for this ticker
            last_daily = session.query(func.max(DailyPrices.datetime)).filter(
                DailyPrices.ticker_id == ticker.id
            ).scalar()

            # Get today's date in EST
            est = pytz.timezone('US/Eastern')
            today_est = datetime.now(est).date()

            # Determine start date for fetching
            if last_daily:
                # Start from the day after the last daily row
                start_date = last_daily.date() + timedelta(days=1)
            else:
                # No daily rows exist - get the earliest intraday price date for this ticker
                first_price = session.query(func.min(Price.datetime)).filter(
                    Price.ticker_id == ticker.id
                ).scalar()
                if first_price:
                    start_date = first_price.date()
                else:
                    # No price data at all - skip this ticker
                    with self.lock:
                        self.processed += 1
                    return 0

            # Skip if already up to date
            if start_date > today_est:
                with self.lock:
                    self.processed += 1
                return 0

            # Fetch daily data from start_date to today
            daily_data = self.fmp_api.get_daily_prices_for_ticker(
                ticker.ticker,
                datetime.combine(start_date, dt_time(0, 0)),
                datetime.combine(today_est, dt_time(23, 59))
            )

            if not daily_data or 'historical' not in daily_data or not daily_data['historical']:
                with self.lock:
                    self.processed += 1
                return 0

            # Build records for all days returned
            records = []
            for day_data in daily_data['historical']:
                date_str = day_data.get('date')
                if not date_str:
                    continue

                # Parse the date - store as datetime at midnight UTC for consistency
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                records.append({
                    'ticker_id': str(ticker.id),
                    'datetime': date_obj,
                    'open': day_data.get('open'),
                    'high': day_data.get('high'),
                    'low': day_data.get('low'),
                    'close': day_data.get('close'),
                    'adj_close': day_data.get('adjClose'),
                    'volume': day_data.get('volume')
                })

            if not records:
                with self.lock:
                    self.processed += 1
                return 0

            # Bulk insert daily records, skip duplicates
            stmt = insert(DailyPrices).values(records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'datetime'])
            result = session.execute(stmt)
            session.commit()

            with self.lock:
                self.processed += 1
                if result.rowcount > 0:
                    self.successful_updates += 1
                    self.total_records += result.rowcount

                if self.processed % 50 == 0:
                    print(f"Daily Prices Progress: {self.processed}/{self.total_tickers} tickers processed")

            return result.rowcount

        except Exception as e:
            print(f"Error updating daily prices for {ticker.ticker}: {str(e)}")
            session.rollback()
            with self.lock:
                self.errors += 1
            return -1
        finally:
            session.close()

    def recover_ticker_data(self, ticker_symbol: str):
        """
        Recover data for a specific ticker by re-fetching from FMP API.

        Args:
            ticker_symbol: Ticker symbol (e.g., 'VIXY', 'AAPL')

        Returns:
            int: Number of records inserted, -1 on error, 0 if no new data
        """
        print("="*70)
        print(f"DATA RECOVERY FOR {ticker_symbol}")
        print("="*70)

        # Get ticker from database
        session = MarketSession()
        ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()

        if not ticker:
            print(f"❌ ERROR: Ticker '{ticker_symbol}' not found in database")
            session.close()
            return -1

        ticker_id = str(ticker.id)
        print(f"\n✓ Found {ticker_symbol}")
        print(f"  Ticker ID: {ticker_id}")

        # Get the last date we have data for
        last_date = session.query(func.max(Price.datetime)).filter(
            Price.ticker_id == ticker.id
        ).scalar()

        if not last_date:
            print(f"\n⚠️  No existing price data found for {ticker_symbol}")
            print("Cannot determine recovery start date.")
            session.close()
            return -1

        # Get total records before recovery
        records_before = session.query(func.count(Price.datetime)).filter(
            Price.ticker_id == ticker.id
        ).scalar()

        print(f"  Last date in DB: {last_date}")
        print(f"  Records before recovery: {records_before}")

        session.close()

        # Fetch and insert new data
        print(f"\n📡 Fetching data from {last_date} to current time...")
        print("   (FMP API will return EST data, automatically converted to UTC)")

        records_inserted = self.update_prices_for_single_ticker(ticker_id, last_date)

        # Show results
        print("\n" + "="*70)
        print("RECOVERY RESULTS")
        print("="*70)

        if records_inserted > 0:
            print(f"✅ SUCCESS!")
            print(f"   New records inserted: {records_inserted}")
            print(f"   Total records now: {records_before + records_inserted}")

            # Verify the new last date
            session = MarketSession()
            new_last_date = session.query(func.max(Price.datetime)).filter(
                Price.ticker_id == ticker.id
            ).scalar()
            session.close()

            print(f"   Updated last date: {new_last_date}")

        elif records_inserted == 0:
            print(f"⚠️  No new data available")
            print("   Possible reasons:")
            print("   - Data is already up to date")
            print("   - No trading activity since last update")
            print("   - API returned no new records")

        else:
            print(f"❌ ERROR occurred during recovery")
            print("   Check the error messages above for details")

        print("="*70)
        return records_inserted


def get_current_est_time() -> datetime:
    """Get the current datetime in EST timezone."""
    est = pytz.timezone('US/Eastern')
    return datetime.now(est)


def is_after_market_close() -> bool:
    """Check if current EST time is after market close (5PM EST)."""
    current_est = get_current_est_time()
    return current_est.hour >= 17


def run_price_updates(max_workers: int = 10):
    """
    Run price table updates based on current EST time.

    - Before 5PM EST: Update 15-min intraday prices only
    - 5PM EST or later: Update 15-min intraday prices AND daily EOD prices
    """
    updater = UpdatePriceTable()
    current_est = get_current_est_time()
    current_hour = current_est.hour

    print(f"\n{'='*50}")
    print(f"PRICE TABLE UPDATE JOB")
    print(f"{'='*50}")
    print(f"Current EST Time: {current_est.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Current Hour: {current_hour}")

    if current_hour < 17:
        print(f"Status: BEFORE 5PM EST - Running intraday update only")
        print(f"{'='*50}\n")

        # Before 5PM: Only update 15-min intraday prices
        updater.update_all_ticker_prices(max_workers=max_workers)
    else:
        print(f"Status: 5PM EST OR LATER - Running intraday + EOD updates")
        print(f"{'='*50}\n")

        # 5PM or later: Update both intraday and daily prices
        updater.update_all_ticker_prices(max_workers=max_workers)
        updater.update_daily_prices(max_workers=max_workers)

    print(f"\n{'='*50}")
    print(f"ALL PRICE UPDATES COMPLETE")
    print(f"{'='*50}")


if __name__ == "__main__":
    run_price_updates(max_workers=8)
