from backend.src.repositories.market_data.ticker_repository import get_ticker_price_data
from backend.src.db.core.db_config import MarketSession, market_engine
from backend.src.db.core.market_data_models import Ticker, Price
from datetime import datetime, timedelta
from sqlalchemy import insert, extract, text
from backend.src.db.core.pull_fmp_data import FMP_API_DATA
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import csv
import sys

class TransferPriceData:
    def __init__(self, ticker):
        self.ticker = ticker
        self.start_date = '1900-01-01'
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.interval = '15T'
        self.batch_size = 2000  # Optimal batch size for PostgreSQL

    def get_current_price_data(self):
        all_data_for_aapl = get_ticker_price_data(self.ticker, self.start_date, self.end_date, self.interval)
        print(all_data_for_aapl)

    def push_price_data_to_db(self):
        session = MarketSession()
        try:
            ticker_obj = session.query(Ticker).filter(Ticker.ticker == self.ticker).first()
            if not ticker_obj:
                print(f"✗ Ticker {self.ticker} not found in database")
                return self.ticker, False, "Not found"
            
            print(f"  DEBUG - Ticker object found:")
            print(f"    ticker_obj.id: {ticker_obj.id}")
            print(f"    ticker_obj.id type: {type(ticker_obj.id)}")
            print(f"    ticker_obj.ticker: {ticker_obj.ticker}")

            existing_price = session.query(Price).filter(Price.ticker_id == ticker_obj.id).first()
            if existing_price:
                # Get count of existing records
                existing_count = session.query(Price).filter(Price.ticker_id == ticker_obj.id).count()
                print(f"⏭️  Skipping {self.ticker} - already has {existing_count:,} price records")
                return self.ticker, True, f"Skipped - {existing_count:,} records exist"

            print(f"\n📊 Processing {self.ticker}...")
            all_data = get_ticker_price_data(self.ticker, self.start_date, self.end_date, self.interval)

            if all_data.empty:
                all_data = self.get_intraday_prices_for_ticker()
                if all_data.empty:
                    return self.ticker, False, "No data found ANYWHERE"

            # Debug: Check data structure
            print(f"  Data type: {type(all_data)}")
            print(f"  Data shape: {all_data.shape if hasattr(all_data, 'shape') else 'N/A'}")
            print(f"  Columns: {list(all_data.columns) if hasattr(all_data, 'columns') else 'N/A'}")
            if len(all_data) > 0:
                print(f"  First row sample: {all_data.iloc[0].to_dict() if hasattr(all_data, 'iloc') else 'N/A'}")
                print(f"  Data types: {all_data.dtypes.to_dict() if hasattr(all_data, 'dtypes') else 'N/A'}")

            # Ensure we have required columns
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in all_data.columns]
            if missing_columns:
                print(f"✗ Missing required columns: {missing_columns}")
                return self.ticker, False, f"Missing columns: {missing_columns}"

            # Get date range information
            first_date = all_data['date'].min()
            last_date = all_data['date'].max()
            
            # Use COPY for much faster bulk inserts
            total_rows = len(all_data)
            print(f"Inserting {total_rows:,} rows for {self.ticker}")
            print(f"  Date range: {first_date} to {last_date}")
            
            start_time = time.time()
            rows_inserted = 0
            rows_skipped = 0
            skip_reasons = {}
            
            # Process in batches to avoid memory issues
            for batch_start in range(0, total_rows, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_rows)
                batch_data = all_data.iloc[batch_start:batch_end]
                
                # Debug batch info
                if batch_start == 0:  # Only debug first batch
                    print(f"  DEBUG - First batch info:")
                    print(f"    Batch size: {len(batch_data)}")
                    print(f"    Batch type: {type(batch_data)}")
                    if len(batch_data) > 0:
                        print(f"    First row in batch: {batch_data.iloc[0].to_dict()}")
                
                # Prepare data for COPY
                output = io.StringIO()
                writer = csv.writer(output, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                batch_valid_rows = 0
                batch_errors = []
                
                # Debug before iteration
                if batch_start == 0:
                    print(f"  DEBUG - About to iterate over batch:")
                    print(f"    batch_data type: {type(batch_data)}")
                    print(f"    batch_data empty: {batch_data.empty if hasattr(batch_data, 'empty') else 'N/A'}")
                    print(f"    len(batch_data): {len(batch_data)}")
                    try:
                        print(f"    iterrows available: {hasattr(batch_data, 'iterrows')}")
                    except Exception as e:
                        print(f"    Error checking iterrows: {e}")
                
                row_count = 0
                for idx, row in batch_data.iterrows():
                    row_count += 1
                    if batch_start == 0 and row_count == 1:  # Debug first row of first batch
                        print(f"  DEBUG - First row iteration:")
                        print(f"    idx: {idx}")
                        print(f"    row type: {type(row)}")
                        print(f"    row keys/index: {list(row.index) if hasattr(row, 'index') else 'N/A'}")
                    
                    try:
                        # Validate all fields
                        date_val = row['date']
                        if pd.isna(date_val):
                            skip_reasons['missing_date'] = skip_reasons.get('missing_date', 0) + 1
                            rows_skipped += 1
                            continue
                        
                        # Convert date to datetime if it's not already
                        if isinstance(date_val, pd.Timestamp):
                            datetime_val = date_val.to_pydatetime()
                        elif isinstance(date_val, str):
                            datetime_val = pd.to_datetime(date_val).to_pydatetime()
                        else:
                            datetime_val = pd.to_datetime(date_val).to_pydatetime()
                        
                        # Validate numeric fields
                        open_val = float(row['open']) if pd.notna(row['open']) else None
                        high_val = float(row['high']) if pd.notna(row['high']) else None
                        low_val = float(row['low']) if pd.notna(row['low']) else None
                        close_val = float(row['close']) if pd.notna(row['close']) else None
                        
                        if any(v is None for v in [open_val, high_val, low_val, close_val]):
                            skip_reasons['missing_price'] = skip_reasons.get('missing_price', 0) + 1
                            rows_skipped += 1
                            continue
                        
                        # Handle volume - convert to int, handle NaN and float values
                        volume_val = row['volume']
                        if pd.isna(volume_val):
                            volume = 0
                        else:
                            try:
                                volume = int(float(volume_val))
                            except (ValueError, TypeError):
                                skip_reasons['invalid_volume'] = skip_reasons.get('invalid_volume', 0) + 1
                                rows_skipped += 1
                                continue
                        
                        # Debug first successful row write
                        if batch_start == 0 and batch_valid_rows == 0:
                            print(f"  DEBUG - Writing first valid row:")
                            print(f"    ticker_id: {str(ticker_obj.id)}")
                            print(f"    datetime: {datetime_val}")
                            print(f"    OHLCV: {open_val}, {high_val}, {low_val}, {close_val}, {volume}")
                        
                        writer.writerow([
                            str(ticker_obj.id),  # Convert UUID to string
                            datetime_val,  # Use datetime_val instead of row['date']
                            open_val,
                            high_val,
                            low_val,
                            close_val,
                            volume
                        ])
                        batch_valid_rows += 1
                        
                    except Exception as e:
                        error_type = f'error_{type(e).__name__}'
                        skip_reasons[error_type] = skip_reasons.get(error_type, 0) + 1
                        rows_skipped += 1
                        batch_errors.append(f"{type(e).__name__}: {str(e)}")
                        if len(batch_errors) <= 3:  # Only store first 3 errors per batch
                            print(f"    ⚠️  Error processing row {idx}: {e}")
                            print(f"        Row data: date={row['date'] if 'date' in row else 'N/A'}, "
                                  f"open={row['open'] if 'open' in row else 'N/A'}, "
                                  f"high={row['high'] if 'high' in row else 'N/A'}, "
                                  f"low={row['low'] if 'low' in row else 'N/A'}, "
                                  f"close={row['close'] if 'close' in row else 'N/A'}, "
                                  f"volume={row['volume'] if 'volume' in row else 'N/A'}")
                        continue
                
                output.seek(0)
                
                # Check if we have any data to insert
                buffer_size = len(output.getvalue())
                if buffer_size == 0:
                    print(f"  Warning: No valid data in batch {batch_start}-{batch_end}, skipping")
                    print(f"    Rows processed in batch: {row_count}")
                    print(f"    Valid rows in batch: {batch_valid_rows}")
                    if batch_errors:
                        print(f"    First few errors in batch: {batch_errors[:3]}")
                    continue
                
                output.seek(0)
                
                # Use raw connection for COPY
                raw_conn = market_engine.raw_connection()
                try:
                    cursor = raw_conn.cursor()
                    cursor.copy_expert(
                        """COPY price_data.prices (ticker_id, datetime, open, high, low, close, volume) 
                           FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t')""",
                        output
                    )
                    raw_conn.commit()
                    rows_inserted += batch_valid_rows
                    
                    if rows_inserted % 10000 == 0 or rows_inserted == total_rows - rows_skipped:
                        progress_pct = (rows_inserted / (total_rows - rows_skipped)) * 100 if (total_rows - rows_skipped) > 0 else 0
                        print(f"  Progress: {rows_inserted:,}/{total_rows - rows_skipped:,} valid rows ({progress_pct:.1f}%)")
                    
                except Exception as e:
                    raw_conn.rollback()
                    raise e
                finally:
                    cursor.close()
                    raw_conn.close()
            
            elapsed_time = time.time() - start_time
            rows_per_second = rows_inserted / elapsed_time if elapsed_time > 0 else 0
            
            # Format time nicely
            if elapsed_time < 60:
                time_str = f"{elapsed_time:.1f} seconds"
            else:
                time_str = f"{elapsed_time/60:.1f} minutes"
            
            print(f"✓ Successfully inserted {rows_inserted:,} rows for {self.ticker}")
            print(f"  Date range: {first_date} to {last_date}")
            print(f"  Rows skipped: {rows_skipped:,}")
            if skip_reasons:
                print(f"  Skip reasons: {skip_reasons}")
            print(f"  Time taken: {time_str} ({rows_per_second:,.0f} rows/sec)")
            
            return self.ticker, True, f"Success - {rows_inserted:,} rows inserted, {rows_skipped:,} skipped in {elapsed_time:.1f}s"
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error for {self.ticker}: {str(e)[:100]}...")
            return self.ticker, False, f"Error: {str(e)[:100]}"
        finally:
            session.close()
    
    def get_intraday_prices_for_ticker(self):
        fmp_api = FMP_API_DATA()
        all_data = []
        to_date = datetime.now()
        limit_date = datetime.now() - timedelta(days=6*365)
        last_fetched_date_str = ''

        while to_date > limit_date:
            from_date = to_date - timedelta(weeks=2)
            if from_date < limit_date:
                from_date = limit_date

            print(f"Fetching data for ticker {self.ticker} from {from_date.strftime('%Y-%m-%d %H:%M:%S')} to {to_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
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

    def check_database_health(self):
        """Check database health metrics that could affect performance"""
        print("\n=== Database Health Check ===")
        session = MarketSession()
        
        try:
            # Check connection pool status
            print("\n1. Connection Pool Status:")
            result = session.execute(text("""
                SELECT state, count(*) 
                FROM pg_stat_activity 
                GROUP BY state
                ORDER BY count(*) DESC
            """))
            for row in result:
                print(f"   {row[0] or 'active'}: {row[1]} connections")
            
            # Check autovacuum status for price table
            print("\n2. Vacuum Status for Price Table:")
            result = session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    last_vacuum,
                    last_autovacuum,
                    n_dead_tup,
                    n_live_tup,
                    round(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) as dead_percentage
                FROM pg_stat_user_tables
                WHERE schemaname = 'price_data' AND tablename = 'prices'
            """))
            for row in result:
                print(f"   Last manual vacuum: {row[2]}")
                print(f"   Last autovacuum: {row[3]}")
                print(f"   Dead tuples: {row[4]:,} ({row[6]}%)")
                print(f"   Live tuples: {row[5]:,}")
            
            # Check for long-running transactions
            print("\n3. Long-Running Transactions:")
            result = session.execute(text("""
                SELECT 
                    pid,
                    age(clock_timestamp(), xact_start) as transaction_age,
                    state,
                    LEFT(query, 60) as query_preview
                FROM pg_stat_activity
                WHERE xact_start IS NOT NULL
                AND age(clock_timestamp(), xact_start) > interval '5 minutes'
                ORDER BY xact_start
                LIMIT 5
            """))
            count = 0
            for row in result:
                count += 1
                print(f"   PID {row[0]}: {row[1]} - {row[2]} - {row[3]}...")
            if count == 0:
                print("   No long-running transactions found (good!)")
            
            # Check table size and bloat estimate
            print("\n4. Price Table Size:")
            result = session.execute(text("""
                SELECT 
                    pg_size_pretty(pg_relation_size('price_data.prices')) as table_size,
                    pg_size_pretty(pg_total_relation_size('price_data.prices')) as total_size_with_indexes
            """))
            for row in result:
                print(f"   Table size: {row[0]}")
                print(f"   Total size with indexes: {row[1]}")
                
            print("\n=== End Health Check ===\n")
            
        except Exception as e:
            print(f"Error during health check: {e}")
        finally:
            session.close()


if __name__ == "__main__":
    last_ticker = 'SPHB'
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        if '--health-check' in sys.argv:
            print("Running database health check...")
            transfer = TransferPriceData('')
            transfer.check_database_health()
            if '--health-only' in sys.argv:
                exit(0)
        if '--help' in sys.argv:
            print("Usage: python transfer_price_data.py [options]")
            print("Options:")
            print("  --health-check    Run database health check before transfer")
            print("  --health-only     Only run health check, don't transfer data")
            print("  --help           Show this help message")
            exit(0)
    
    session = MarketSession()

    tickers = session.query(Ticker).all()
    session.close()  # Close session after fetching tickers

    try:
        # Find the index of the ticker
        last_index = [t.ticker for t in tickers].index(last_ticker)

        
        # Process tickers starting from the one after GDX
        # for ticker in tickers[last_index:]:
        #     transfer = TransferPriceData(ticker.ticker)
        #     transfer.push_price_data_to_db()

        tickers_to_process = tickers[last_index:]

        # Process tickers in parallel
        max_workers = 1  # Reduced to avoid connection pool exhaustion
        results = []
        
        print(f"Processing {len(tickers_to_process)} tickers with {max_workers} parallel workers")
        print("=" * 80)
        overall_start = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(
                    lambda t: TransferPriceData(t).push_price_data_to_db(), 
                    ticker.ticker
                ): ticker.ticker 
                for ticker in tickers_to_process
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_ticker):
                ticker_symbol = future_to_ticker[future]
                completed += 1
                try:
                    result = future.result()
                    results.append(result)
                    status_symbol = "✓" if result[1] else "✗"
                    print(f"\n[{completed}/{len(tickers_to_process)}] {status_symbol} {result[0]}: {result[2]}")
                except Exception as exc:
                    print(f"\n[{completed}/{len(tickers_to_process)}] ✗ {ticker_symbol}: Exception - {exc}")
                    results.append((ticker_symbol, False, f"Exception: {exc}"))
        
        # Summary
        overall_elapsed = time.time() - overall_start
        print("\n" + "=" * 80)
        print("PROCESSING SUMMARY")
        print("=" * 80)
        
        success_count = sum(1 for r in results if r[1])
        failed_count = len(results) - success_count
        
        print(f"Total tickers processed: {len(results)}")
        print(f"  ✓ Successful: {success_count}")
        print(f"  ✗ Failed/Skipped: {failed_count}")
        
        # Calculate total rows inserted
        total_rows_inserted = 0
        for result in results:
            if result[1] and "rows" in result[2]:
                # Extract number of rows from success message
                try:
                    rows_str = result[2].split(" rows")[0].split(" - ")[1].replace(",", "")
                    total_rows_inserted += int(rows_str)
                except:
                    pass
        
        print(f"\nTotal rows inserted: {total_rows_inserted:,}")
        
        # Time formatting
        if overall_elapsed < 60:
            time_str = f"{overall_elapsed:.1f} seconds"
        elif overall_elapsed < 3600:
            time_str = f"{overall_elapsed/60:.1f} minutes"
        else:
            time_str = f"{overall_elapsed/3600:.1f} hours"
        
        print(f"\nTotal time: {time_str}")
        if len(results) > 0:
            print(f"Average time per ticker: {overall_elapsed/len(results):.1f} seconds")
        if overall_elapsed > 0 and total_rows_inserted > 0:
            print(f"Overall throughput: {total_rows_inserted/overall_elapsed:,.0f} rows/second")
        
        print("=" * 80)

    except ValueError:
        print(f"Ticker '{last_ticker}' not found, so no tickers were processed.")

    
