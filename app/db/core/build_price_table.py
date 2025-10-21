from app.repositories.price_data import get_price_data_15_mins
from app.db.core.db_config import MarketSession, market_engine
from app.db.core.models.market_data_models import Ticker, Price
from datetime import datetime, timedelta
from sqlalchemy import insert, extract, text
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time, get_utc_date_str
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import csv
import sys
from pathlib import Path

def bulk_insert_with_copy(session, table_name, data_to_insert):
    """
    Performs a bulk insert using PostgreSQL's COPY command for high performance.
    """
    if not data_to_insert:
        print("No new data to insert.")
        return

    print(f"Preparing to insert {len(data_to_insert):,} records using COPY.")
    
    ordered_columns = ['ticker_id', 'datetime', 'open', 'high', 'low', 'close', 'volume']
    
    string_buffer = io.StringIO()
    writer = csv.writer(string_buffer)
    
    for row_dict in data_to_insert:
        writer.writerow([row_dict.get(col) for col in ordered_columns])
        
    string_buffer.seek(0)
    
    raw_connection = session.connection().connection
    cursor = raw_connection.cursor()
    
    try:
        copy_sql = f"COPY {table_name} ({','.join(ordered_columns)}) FROM STDIN WITH (FORMAT CSV)"
        cursor.copy_expert(sql=copy_sql, file=string_buffer)
        raw_connection.commit()
        print("✅ Bulk insertion successful.")
    except Exception as e:
        print(f"An error occurred during COPY: {e}")
        raw_connection.rollback()
    finally:
        cursor.close()

class TransferPriceData:
    def __init__(self, ticker):
        self.ticker = ticker
        self.start_date = '1900-01-01'
        self.end_date = get_utc_date_str()  # Use UTC date
        self.interval = '15T'
        self.batch_size = 2000  # Optimal batch size for PostgreSQL

    def _format_data(self, ticker_id, all_data):
        """Formats DataFrame and returns a list of dictionaries for insertion."""
        all_data['ticker_id'] = ticker_id
        all_data.rename(columns={'date': 'datetime'}, inplace=True)

        for col in ['open', 'high', 'low', 'close']:
            all_data[col] = pd.to_numeric(all_data[col], errors='coerce')
        
        all_data['volume'] = pd.to_numeric(all_data['volume'], errors='coerce').fillna(0).astype(int)

        return all_data.to_dict('records')

    def get_current_price_data(self):
        # Convert string dates to datetime objects
        start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
        
        all_data_for_aapl = get_price_data_15_mins(self.ticker, start_dt, end_dt)
        print(all_data_for_aapl)
        return all_data_for_aapl

    def prepare_price_data_for_db(self, session):
        """
        Prepares price data for a ticker to be inserted into the DB.
        This method checks for existing data and fetches new data if needed.
        It does NOT commit the transaction.
        """
        try:
            ticker_obj = session.query(Ticker).filter(Ticker.ticker == self.ticker).first()
            if not ticker_obj:
                print(f"[{self.ticker}] ✗ Not found in ticker table")
                return None, "Not found"

            existing_price = session.query(Price).filter(Price.ticker_id == ticker_obj.id).first()
            if existing_price:
                existing_count = session.query(Price).filter(Price.ticker_id == ticker_obj.id).count()
                print(f"[{self.ticker}] 🐬 {existing_count:,} records exist in price table")
                return None, "Skipped"

            print(f"[{self.ticker}] 🚀 Fetching data...")
            all_data = self.get_current_price_data()

            if all_data.empty:
                all_data = self.get_intraday_prices_for_ticker()
            
            if all_data.empty:
                return None, "No data found"

            formatted_data = self._format_data(ticker_obj.id, all_data)
            return formatted_data, "Success"

        except Exception as e:
            print(f"[{self.ticker}] ✗ Error: {e}")
            return None, str(e)
    
    def get_intraday_prices_for_ticker(self):
        fmp_api = FMP_API_DATA()
        all_data = []
        to_date = get_current_utc_time()  # Use UTC time
        limit_date = get_current_utc_time() - timedelta(days=6*365)  # Use UTC time
        last_fetched_date_str = ''

        while to_date > limit_date:
            from_date = to_date - timedelta(weeks=2)
            if from_date < limit_date:
                from_date = limit_date

            print(f"[{self.ticker}] Fetching data from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
            
            price_chunk = fmp_api.get_intraday_prices_for_ticker(
                ticker=self.ticker,
                from_date=from_date,
                to_date=to_date
            )

            if not price_chunk:
                print("No more data found for this period. Stopping.")
                break

            all_data.extend(price_chunk)

            oldest_date_str = price_chunk[-1]['date']

            if oldest_date_str == last_fetched_date_str:
                print("Fetched the same data twice, indicates end of available data. Stopping.")
                break
            last_fetched_date_str = oldest_date_str
            
            to_date = datetime.strptime(oldest_date_str, '%Y-%m-%d %H:%M:%S')

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df.drop_duplicates(subset=['date'], inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values(by='date', inplace=True)
        
        return df

if __name__ == "__main__":
    # Use Path to reference the ticker file in the same directory
    ticker_file = Path(__file__).parent / "tickers_with_no_data.txt"
    num_tickers_to_process = 25

    for i in range(40):
        try:
            with open(ticker_file, 'r') as f:
                all_tickers_from_file = [line.strip() for line in f if line.strip()]
            
            tickers_to_process_symbols = all_tickers_from_file[:num_tickers_to_process]
            remaining_tickers = all_tickers_from_file[num_tickers_to_process:]

            print(f"Tickers to process: {tickers_to_process_symbols}")

            all_price_data_to_insert = []
            session = MarketSession()
            processed_tickers = []
            try:
                for ticker_symbol in tickers_to_process_symbols:
                    transfer = TransferPriceData(ticker_symbol)
                    price_data, status = transfer.prepare_price_data_for_db(session)
                    
                    if status == "Success" and price_data:
                        all_price_data_to_insert.extend(price_data)
                        processed_tickers.append(ticker_symbol)

                start_time = time.time()
                
                chunk_size = 5000
                total_rows = len(all_price_data_to_insert)

                if total_rows > 0:
                    print(f"Total rows to insert: {total_rows:,}. Processing in chunks of {chunk_size:,}.")
                    for i in range(0, total_rows, chunk_size):
                        chunk = all_price_data_to_insert[i:i + chunk_size]
                        print(f"--- Processing chunk {i//chunk_size + 1}/{(total_rows + chunk_size - 1)//chunk_size} (rows {i+1}-{i+len(chunk)}) ---")
                        bulk_insert_with_copy(session, Price.__table__.fullname, chunk)
                else:
                    print("No new data to insert.")

                end_time = time.time()
                duration = end_time - start_time
                
                if total_rows > 0:
                    print(f"⌛ Total insertion time for all chunks: {duration:.2f} seconds.")

            except Exception as e:
                print(f"An error occurred during batch processing: {e}")
            finally:
                session.close()

            with open(ticker_file, 'w') as f:
                for ticker in remaining_tickers:
                    f.write(f"{ticker}\n")

            print(f"Successfully processed batch. {len(remaining_tickers)} tickers remaining.")

        except FileNotFoundError:
            print(f"Error: The file '{ticker_file}' was not found.")
            exit(1)
        
        time.sleep(10)




     

   