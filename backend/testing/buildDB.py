import sys
import os
import time
import traceback
from datetime import datetime, timedelta

# Add project root to sys.path to allow for absolute imports
# This makes the script runnable from any directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from ib_insync import IB, Stock, util
from backend.src.utils.ib_utils import connect_to_ib, disconnect_from_ib
import json
import psycopg2
from backend.src.utils.database import execute_bulk_insert, get_db_connection
import numpy
from psycopg2.extensions import register_adapter

# Adapters for NumPy data types to Python native types
def adapt_numpy_int64(np_int64):
    return psycopg2.extensions.AsIs(int(np_int64))

def adapt_numpy_float64(np_float64):
    return psycopg2.extensions.AsIs(float(np_float64))

# Register the adapters with psycopg2
register_adapter(numpy.int64, adapt_numpy_int64)
register_adapter(numpy.int32, adapt_numpy_int64) # Handle 32-bit ints as well
register_adapter(numpy.float64, adapt_numpy_float64)
register_adapter(numpy.float32, adapt_numpy_float64) # Handle 32-bit floats

def get_5y_data(ib, symbol):
    try:
        contract = Stock(symbol, 'SMART', 'USD')
        
        # Helper function to safely convert to DataFrame and check if empty
        def safe_convert_and_check(bars_data):
            if bars_data is None:
                return None
            
            # If it's already a DataFrame, just check if it's empty
            if isinstance(bars_data, pd.DataFrame):
                return None if bars_data.empty else bars_data
                
            # If it's a BarDataList from IB, convert to DataFrame
            try:
                df = util.df(bars_data)
                return None if df.empty else df
            except Exception as e:
                print(f"Error converting data: {e}")
                return None
            
        # Rest of your get_date function remains the same
        def get_date(df):
            if df is None or df.empty:
                return None
            
            if 'date' in df.columns:
                first_date_str = df['date'].iloc[0]
                first_date = pd.to_datetime(first_date_str)
                print(f"First date in data: {first_date}")

                # Calculate the day before
                previous_date = first_date.date() - timedelta(days=1)
                previous_date = str(previous_date).replace('-', '')
                print(f"Date from the day before: {previous_date}")
                return previous_date
            else:
                print("No date column found.")
                return None

        # YEAR 1
        try:
            bars_raw = ib.reqHistoricalData(
                contract, 
                endDateTime='',
                durationStr='1 Y', 
                barSizeSetting='15 mins', 
                whatToShow='TRADES', 
                useRTH=False,
                formatDate=1
            )
            
            # Safely convert to DataFrame
            bars = safe_convert_and_check(bars_raw)
            if bars is None:
                print(f"⚠️ No valid data for {symbol} in first year")
                return None
                
            # Add datetime column and filter
            bars['datetime'] = pd.to_datetime(bars['date'])
            # Keep only data between 9:30 AM and 4:00 PM ET
            bars = bars[
                (bars['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                (bars['datetime'].dt.time <= pd.to_datetime('16:00').time())
            ]
            
            if bars.empty:
                print(f"⚠️ No valid trading hours data for {symbol}")
                return None
                
            previous_date = get_date(bars)
            if not previous_date:
                print(f"⚠️ Could not determine previous date for {symbol}")
                return bars  # Return what we have so far
                
        except Exception as e:
            print(f"⚠️ Error fetching first year data for {symbol}: {e}")
            return None

        time.sleep(1)

        # Initialize DataFrames for additional years
        bars2, bars3, bars4, bars5 = None, None, None, None
        
        # YEAR 2
        try:
            bars2_raw = ib.reqHistoricalData(
                contract, 
                endDateTime=previous_date + ' 18:00:00',
                durationStr='1 Y', 
                barSizeSetting='15 mins', 
                whatToShow='TRADES', 
                useRTH=False,
                formatDate=1
            )
            
            # Safely convert to DataFrame
            bars2 = safe_convert_and_check(bars2_raw)
            if bars2 is None:
                print(f"No data returned for {symbol} in second year - continuing with first year data only")
            else:
                bars2['datetime'] = pd.to_datetime(bars2['date'])
                # Filter trading hours
                bars2 = bars2[
                    (bars2['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                    (bars2['datetime'].dt.time <= pd.to_datetime('16:00').time())
                ]
                
                if bars2.empty:
                    bars2 = None
                    print(f"No valid trading hours data for {symbol} in second year")
                    previous_date2 = None
                else:
                    previous_date2 = get_date(bars2)
            
        except Exception as e:
            print(f"Error fetching second year data for {symbol}: {e} - continuing with available data")
            previous_date2 = None
            bars2 = None

        time.sleep(1)

        # YEAR 3 - Only proceed if we have previous_date2
        if previous_date2:
            try:
                bars3_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date2 + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                bars3 = safe_convert_and_check(bars3_raw)
                if bars3 is None:
                    print(f"No data returned for {symbol} in third year - continuing with available data")
                    previous_date3 = None
                else:
                    bars3['datetime'] = pd.to_datetime(bars3['date'])
                    bars3 = bars3[
                        (bars3['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars3['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars3.empty:
                        bars3 = None
                        print(f"No valid trading hours data for {symbol} in third year")
                        previous_date3 = None
                    else:
                        previous_date3 = get_date(bars3)
                
            except Exception as e:
                print(f"Error fetching third year data for {symbol}: {e} - continuing with available data")
                previous_date3 = None
                bars3 = None
        else:
            previous_date3 = None
            bars3 = None

        time.sleep(1)

        # YEAR 4 - Only proceed if we have previous_date3
        if previous_date3:
            try:
                bars4_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date3 + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                bars4 = safe_convert_and_check(bars4_raw)
                if bars4 is None:
                    print(f"No data returned for {symbol} in fourth year - continuing with available data")
                    previous_date4 = None
                else:
                    bars4['datetime'] = pd.to_datetime(bars4['date'])
                    bars4 = bars4[
                        (bars4['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars4['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars4.empty:
                        bars4 = None
                        print(f"No valid trading hours data for {symbol} in fourth year")
                        previous_date4 = None
                    else:
                        previous_date4 = get_date(bars4)
                
            except Exception as e:
                print(f"Error fetching fourth year data for {symbol}: {e} - continuing with available data")
                previous_date4 = None
                bars4 = None
        else:
            previous_date4 = None
            bars4 = None

        time.sleep(1)

        # YEAR 5 - Only proceed if we have previous_date4
        if previous_date4:
            try:
                bars5_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date4 + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                bars5 = safe_convert_and_check(bars5_raw)
                if bars5 is None:
                    print(f"No data returned for {symbol} in fifth year - continuing with available data")
                else:
                    bars5['datetime'] = pd.to_datetime(bars5['date'])
                    bars5 = bars5[
                        (bars5['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars5['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars5.empty:
                        bars5 = None
                        print(f"No valid trading hours data for {symbol} in fifth year")
                
            except Exception as e:
                print(f"Error fetching fifth year data for {symbol}: {e} - continuing with available data")
                bars5 = None
        else:
            bars5 = None

        # Prepare list of DataFrames to concatenate
        # This is where the error was occurring - now we've already ensured all are DataFrames
        dfs_to_concat = []
        for i, df in enumerate([bars, bars2, bars3, bars4, bars5], 1):
            if df is not None and not df.empty:
                dfs_to_concat.append(df)
                print(f"✅ Year {i} data will be included: {len(df)} rows")
            else:
                print(f"❌ Year {i} data not available")
        
        if not dfs_to_concat:
            print(f"⚠️ No valid data frames to concatenate for {symbol}")
            return None
        
        # Concatenate the DataFrames and sort by datetime
        print(f"🔄 Combining data from {len(dfs_to_concat)} years...")
        combined_bars = pd.concat(dfs_to_concat, ignore_index=True)
        combined_bars = combined_bars.sort_values('datetime').reset_index(drop=True)
        # Remove any duplicate rows based on datetime
        combined_bars = combined_bars.drop_duplicates(subset='datetime', keep='first')
        print(f"📊 Combined and deduplicated bars for {symbol}: {len(combined_bars)} records")
        
        if len(combined_bars) > 0:
            print(combined_bars.head())
            if len(combined_bars) > 5:
                print("...")
                print(combined_bars.tail())
        else:
            print("No data available.")
        
        return combined_bars
        
    except Exception as e:
        print(f"⚠️ Unexpected error in get_5y_data for {symbol}: {e}")
        traceback.print_exc()
        return None

def get_etf_tickers_by_asset_class(asset_class: str) -> list:
    """
    Reads the database_schemas.json file and returns a list of tickers for a given ETF asset class.
    """
    try:
        json_path = os.path.join(PROJECT_ROOT, 'backend', 'src', 'data', 'database', 'database_schemas.json')
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {json_path} was not found.")
        return []

    tickers = []
    asset_class_data = data.get('etf_data', {}).get('schemas', {}).get(asset_class, {})
    if asset_class_data:
        sectors = asset_class_data.get('tables', {})
        for sector_name, sector_data in sectors.items():
            tickers.extend(sector_data.get('tickers', []))

    return list(set(tickers))

def create_price_table_for_ticker(db_conn, asset_class: str, table_name: str):
    """
    Creates a new schema and table for a ticker to store its price data.
    """
    try:
        with db_conn.cursor() as cursor:
            # Create schema if it does not exist
            schema_query = f"CREATE SCHEMA IF NOT EXISTS {asset_class};"
            cursor.execute(schema_query)
            
            # Create table
            table_query = f"""
            CREATE TABLE IF NOT EXISTS {asset_class}.{table_name} (
                datetime TIMESTAMP PRIMARY KEY,
                open NUMERIC(10,3),
                high NUMERIC(10,3),
                low NUMERIC(10,3),
                close NUMERIC(10,3),
                volume BIGINT,
                barCount INTEGER,
                average NUMERIC(10,3)
            );
            """
            cursor.execute(table_query)
            db_conn.commit()
            print(f"Table {asset_class}.{table_name} checked/created.")
            return True
    except psycopg2.Error as e:
        print(f"Database error while creating table {asset_class}.{table_name}: {e}")
        db_conn.rollback()
        return False


def run_etf_population(asset_class: str, start_from_ticker: str = None):
    """
    Populates price data for all ETFs in a given asset class.
    
    Args:
        asset_class (str): The asset class to process (e.g., 'fixed_income_etfs')
        start_from_ticker (str, optional): Ticker to start from (useful for resuming interrupted uploads)
    """
    tickers = get_etf_tickers_by_asset_class(asset_class)
    if not tickers:
        print(f"No tickers found for asset class {asset_class}")
        return

    # Sort tickers to ensure consistent order
    tickers.sort()
    
    # Get list of unprocessed tickers
    print("🔍 Checking which tickers are already processed...")
    unprocessed_tickers = []
    
    try:
        with get_db_connection('etf_prices') as db_conn:
            if not db_conn:
                print("Could not connect to the etf_prices database.")
                return
                
            with db_conn.cursor() as cursor:
                for ticker in tickers:
                    table_name = ticker.lower()
                    # Check if table exists and has data
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_name = %s
                    """, (asset_class, table_name))
                    
                    table_exists = cursor.fetchone()[0] > 0
                    
                    if table_exists:
                        # Check if table has data
                        cursor.execute(f"SELECT COUNT(*) FROM {asset_class}.{table_name}")
                        row_count = cursor.fetchone()[0]
                        
                        if row_count == 0:
                            unprocessed_tickers.append(ticker)
                    else:
                        unprocessed_tickers.append(ticker)
                        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    if not unprocessed_tickers:
        print("🎉 All tickers have already been processed!")
        return
    
    print(f"📊 Found {len(tickers)} total tickers, {len(unprocessed_tickers)} unprocessed")
    print(f"📋 Unprocessed tickers: {unprocessed_tickers}")
    
    # If start_from_ticker is specified, find the starting position in unprocessed list
    start_index = 0
    if start_from_ticker:
        if start_from_ticker in unprocessed_tickers:
            start_index = unprocessed_tickers.index(start_from_ticker)
            print(f"📍 Resuming from ticker: {start_from_ticker} (position {start_index + 1}/{len(unprocessed_tickers)} in unprocessed list)")
        else:
            if start_from_ticker in tickers:
                print(f"✅ Ticker {start_from_ticker} has already been processed. Starting from first unprocessed ticker.")
            else:
                print(f"⚠️ Ticker {start_from_ticker} not found in {asset_class}.")
            print(f"🔄 Starting from first unprocessed ticker: {unprocessed_tickers[0]}")
    
    # Get the subset of unprocessed tickers to process
    tickers_to_process = unprocessed_tickers[start_index:]
    
    print(f"🚀 Processing {len(tickers_to_process)} unprocessed tickers starting from position {start_index + 1}")
    print(f"📝 Tickers to process: {tickers_to_process}")

    ib = connect_to_ib()
    if not ib:
        return

    try:
        with get_db_connection('etf_prices') as db_conn:
            if not db_conn:
                print("Could not connect to the etf_prices database.")
                return

            for i, ticker in enumerate(tickers_to_process, 1):
                print(f"--- Processing ticker: {ticker} ({i}/{len(tickers_to_process)} remaining) ---")
                data = get_5y_data(ib, ticker)
                
                if data is not None and not data.empty:
                    table_name = ticker.lower()
                    
                    if not create_price_table_for_ticker(db_conn, asset_class, table_name):
                        print(f"Skipping ticker {ticker} due to table creation error.")
                        continue

                    if 'date' in data.columns:
                        data = data.drop(columns=['date'])
                    
                    ordered_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'barCount', 'average']
                    data = data[ordered_columns]
                    
                    # Round price columns to 3 decimal places
                    price_columns = ['open', 'high', 'low', 'close', 'average']
                    for col in price_columns:
                        data[col] = data[col].round(3)
                    
                    data_to_insert = [tuple(x) for x in data.to_records(index=False)]

                    if data_to_insert:
                        insert_query = f"""
                        INSERT INTO {asset_class}.{table_name} (datetime, open, high, low, close, volume, barCount, average) 
                        VALUES %s
                        ON CONFLICT (datetime) DO NOTHING;
                        """
                        
                        success = execute_bulk_insert(
                            dbname='etf_prices',
                            query=insert_query,
                            data=data_to_insert
                        )
                        
                        if success:
                            print(f"✅ Successfully inserted/updated {len(data_to_insert)} rows for {ticker} into {asset_class}.{table_name}")
                        else:
                            print(f"⚠️ Failed to insert data for {ticker}")
                    else:
                        print(f"No data to insert for {ticker}")

                else:
                    print(f"⚠️ No data received from get_5y_data for {ticker}. Skipping.")
                
                time.sleep(2) # To respect IB's pacing limitations
    finally:
        if ib:
            disconnect_from_ib()
            print("Disconnected from IB")

def display_tickers_for_asset_class(asset_class: str):
    """
    Display all available tickers for a given asset class in a formatted way.
    """
    tickers = get_etf_tickers_by_asset_class(asset_class)
    if not tickers:
        print(f"No tickers found for asset class {asset_class}")
        return
    
    tickers.sort()
    print(f"\n=== Available tickers for {asset_class} ({len(tickers)} total) ===")
    for i, ticker in enumerate(tickers, 1):
        print(f"{i:2d}. {ticker}")
    print("=" * 50)

def check_processed_tickers(asset_class: str):
    """
    Check which tickers have already been processed and stored in the database.
    """
    tickers = get_etf_tickers_by_asset_class(asset_class)
    if not tickers:
        print(f"No tickers found for asset class {asset_class}")
        return

    tickers.sort()
    print(f"\n=== Checking processed status for {asset_class} ({len(tickers)} total) ===")
    
    processed = []
    not_processed = []
    
    try:
        with get_db_connection('etf_prices') as db_conn:
            if not db_conn:
                print("Could not connect to the etf_prices database.")
                return
                
            with db_conn.cursor() as cursor:
                for ticker in tickers:
                    table_name = ticker.lower()
                    # Check if table exists and has data
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_name = %s
                    """, (asset_class, table_name))
                    
                    table_exists = cursor.fetchone()[0] > 0
                    
                    if table_exists:
                        # Check if table has data
                        cursor.execute(f"SELECT COUNT(*) FROM {asset_class}.{table_name}")
                        row_count = cursor.fetchone()[0]
                        
                        if row_count > 0:
                            processed.append((ticker, row_count))
                        else:
                            not_processed.append(ticker)
                    else:
                        not_processed.append(ticker)
                        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    print(f"\n✅ PROCESSED TICKERS ({len(processed)}):")
    for ticker, count in processed:
        print(f"   {ticker}: {count:,} records")
    
    print(f"\n❌ NOT PROCESSED TICKERS ({len(not_processed)}):")
    for ticker in not_processed:
        print(f"   {ticker}")
    
    if not_processed:
        print(f"\n📍 To resume processing, you can start from: {not_processed[0]}")
        print(f"   Use: run_etf_population('{asset_class}', start_from_ticker='{not_processed[0]}')")
    else:
        print(f"\n🎉 All tickers have been processed!")
    
    return not_processed


if __name__ == "__main__":
    # STEP 1: Check which tickers are already processed
    # check_processed_tickers('fixed_income_etfs')
    
    # STEP 2: To see all available tickers in fixed_income_etfs:
    # display_tickers_for_asset_class('fixed_income_etfs')
    
    # STEP 3: Run the population function
    # To start from the beginning:
    # run_etf_population('fixed_income_etfs')
    
    # To resume from a specific ticker:
    # run_etf_population('fixed_income_etfs', start_from_ticker='TICKER_NAME')
    
    # Currently running - Resume from BND (15 remaining tickers):
    # check_processed_tickers('fixed_income_etfs')
    # run_etf_population('fixed_income_etfs', start_from_ticker='BND') 
    run_etf_population('cryptocurrency_etfs')