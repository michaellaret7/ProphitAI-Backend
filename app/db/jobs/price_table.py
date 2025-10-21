from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, Price
from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta, timezone
import time
from app.utils.serialize_output import serialize_sqlalchemy_obj
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


if __name__ == "__main__":
    update_price_table = UpdatePriceTable()
    
    # First show the current state
    last_price_dict = update_price_table.create_last_price_dict()
    print(f"Found {len(last_price_dict)} tickers with price data\n")
    
    update_price_table.update_all_ticker_prices(max_workers=10)


