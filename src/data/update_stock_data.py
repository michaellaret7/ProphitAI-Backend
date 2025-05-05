"""
Author: @Michael Laret
=====================================================================
Update stock data from IBKR to the database.
Purpose of this is to run it every couple days to keep the database up to date.
This file takes the most recent price data from the database and then requests the most recent data from IBKR.
It then updates the database with the new data.
"""
import os
import sys
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from ib_insync import IB, Stock, util
from dotenv import load_dotenv
import time  # Re-add time for timing functionality
from src.utils.ib_utils import get_ib
from src.utils.database import get_default_db_config
from src.utils.file_utils import load_schema_data
import io # Add io for StringIO
import csv # Add csv for COPY formatting
from psycopg2.extras import execute_values # Add import for execute_values
import json # Add json for loading prices schema

# Load environment variables from .env file
load_dotenv()

def get_last_data_date(ticker_location, ticker, db_config):
    """
    Get the last date of OHLC data for a ticker in the database.
    
    Args:
        ticker_location (dict): Dictionary with database location info
        ticker (str): Ticker symbol
        db_config (dict): Database configuration
        
    Returns:
        datetime: Last date of data or None if no data exists
    """
    try:
        # Connect to database
        db_config['dbname'] = ticker_location['database']
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Query the latest datetime
        query = f"""
        SELECT MAX(datetime) 
        FROM {ticker_location['schema']}.{ticker.lower()}
        """
        
        cursor.execute(query)
        result = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"Error getting last date for {ticker}: {e}")
        return None

def get_stock_data_from_ib(ib, ticker, start_date=None):
    """
    Get OHLC data for a ticker from IB.
    
    Args:
        ib: IB connection
        ticker (str): Ticker symbol
        start_date (datetime): Start date for data request (None for 'now')
        
    Returns:
        DataFrame: OHLC data from IB, with a 'datetime' column, filtered for market hours (9:30 AM to 4:00 PM).
    """
    # Start timing the IBKR query
    query_start_time = time.time()
    
    # Calculate the appropriate duration string based on start_date
    if start_date:
        # Calculate the exact time difference between now and start_date
        now = datetime.now()
        days_diff = (now - start_date).days
        
        if days_diff <= 0:
            # If start_date is in the future or today, get the most recent data
            duration_str = "1 D"
        else:
            # Dynamically calculate duration based on the time difference
            # Add 1 day to ensure we get all data including today
            days_diff += 1
            
            # Format the duration string as needed by IB API
            if days_diff <= 1:
                duration_str = f"1 D"
            elif days_diff <= 7:
                duration_str = f"{days_diff} D"
            elif days_diff <= 30:
                # For durations more than a week but less than a month, use weeks
                weeks = (days_diff + 6) // 7  # Round up to nearest week
                duration_str = f"{weeks} W"
            elif days_diff <= 365:
                # For durations more than a month but less than a year, use months
                months = (days_diff + 29) // 30  # Round up to nearest month
                duration_str = f"{months} M"
            else:
                # For durations more than a year, use years
                years = (days_diff + 364) // 365  # Round up to nearest year
                duration_str = f"{years} Y"
                
        print(f"Calculated duration string: {duration_str} for time span of {days_diff} days")
    else:
        # If no start date, get last 7 days by default
        duration_str = "7 D"
    
    try:
        # Create contract for the ticker
        contract = Stock(ticker, 'SMART', 'USD')
        
        contract_time = time.time()
        print(f"Contract creation for {ticker} took {contract_time - query_start_time:.3f} seconds")
        
        # Qualify the contract
        try:
            qualify_start_time = time.time()
            qualified_contracts = ib.qualifyContracts(contract)
            qualify_end_time = time.time()
            print(f"Contract qualification for {ticker} took {qualify_end_time - qualify_start_time:.3f} seconds")
            
            if not qualified_contracts:
                print(f"Could not qualify contract for {ticker}")
                return None
            contract = qualified_contracts[0]
        except Exception as e:
            print(f"Error qualifying contract for {ticker}: {e}")
            return None
        
        # Request historical data
        hist_start_time = time.time()
        print(f"Requesting {duration_str} of 15-min data for {ticker}...")
        
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',  # Current time
            durationStr=duration_str,
            barSizeSetting='15 mins',  # 15-minute bars as requested
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1 # Important: formatDate=1 returns datetime objects
        )
        
        hist_end_time = time.time()
        hist_duration = hist_end_time - hist_start_time
        
        if not bars:
            print(f"No data returned for {ticker} (query took {hist_duration:.3f} seconds)")
            return None
            
        # Convert to DataFrame
        df_start_time = time.time()
        df = util.df(bars)
        df_end_time = time.time()
        
        print(f"Received {len(bars)} bars for {ticker} in {hist_duration:.3f} seconds")
        print(f"DataFrame conversion took {df_end_time - df_start_time:.3f} seconds")
        
        # The 'date' column from IBKR with formatDate=1 is already a datetime object.
        # Rename it to 'datetime' to match our primary key.
        if 'date' not in df.columns:
            print(f"Missing 'date' (timestamp) column in data received from IB for {ticker}")
            return None
            
        df.rename(columns={'date': 'datetime'}, inplace=True)
        
        # Ensure it's the correct type (should be already, but belt-and-suspenders)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Filter for market hours only (9:30 AM to 4:00 PM inclusive)
        # Extract hour and minute to avoid ambiguous truth value errors
        df['hour'] = df['datetime'].dt.hour
        df['minute'] = df['datetime'].dt.minute
        
        # Create the filter with simple numeric comparisons
        # Include 9:30 AM to 4:00 PM (including 4:00 PM exactly)
        market_open = (df['hour'] > 9) | ((df['hour'] == 9) & (df['minute'] >= 30))
        market_close = (df['hour'] < 16) | ((df['hour'] == 16) & (df['minute'] == 0))
        market_hours = market_open & market_close
        
        original_count = len(df)
        df = df[market_hours]
        filtered_count = len(df)
        
        # Drop the helper columns
        df = df.drop(columns=['hour', 'minute'])
        
        print(f"Filtered data for market hours (9:30 AM to 4:00 PM): {filtered_count} rows (removed {original_count - filtered_count} rows)")
        
        # Total time for the entire operation
        total_time = time.time() - query_start_time
        print(f"Total IBKR query processing for {ticker} took {total_time:.3f} seconds")
        
        return df
        
    except Exception as e:
        query_end_time = time.time()
        print(f"Error getting data for {ticker} from IB: {e}")
        print(f"Failed query took {query_end_time - query_start_time:.3f} seconds")
        return None
    
# Get database configuration
db_config = get_default_db_config()

# Load schema data
# schema_data = load_schema_data() # Old way using default file
# Explicitly load the prices schema
prices_schema_file = os.path.join('src', 'data', 'database_schemas_prices.json')
try:
    with open(prices_schema_file, 'r') as f:
        prices_schema_data = json.load(f)
    print(f"Successfully loaded prices schema from {prices_schema_file}")
except FileNotFoundError:
    print(f"Error: Prices schema file not found at {prices_schema_file}")
    prices_schema_data = None
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from {prices_schema_file}")
    prices_schema_data = None

# Connect to IB
ib = get_ib()
if not ib:
    print("Failed to connect to Interactive Brokers")
else:
    print(get_stock_data_from_ib(ib, "AAPL", datetime.now() - timedelta(days=1)))

def ensure_ticker_table_exists(ticker, ticker_location, db_config):
    """
    Ensure table exists for the ticker and create it if it doesn't.
    Also attempts to fix the schema if the table exists:
    - Drops the problematic unique date constraint ([ticker]_date_key).
    - Corrects the data type of the 'date' column if it's DATE (should be TIMESTAMP).
    
    Args:
        ticker (str): Ticker symbol
        ticker_location (dict): Dictionary with database location info
        db_config (dict): Database configuration
        
    Returns:
        bool: True if table exists or was created (and schema fixed), False otherwise
    """
    try:
        # Connect to database
        config = db_config.copy()
        config['dbname'] = ticker_location['database']
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        conn.autocommit = False # Use transactions for safety
        
        # Check if table exists
        ticker_lower = ticker.lower()
        schema = ticker_location['schema']
        
        table_exists_query = f"""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = '{schema}' 
            AND table_name = '{ticker_lower}'
        )
        """
        
        cursor.execute(table_exists_query)
        exists = cursor.fetchone()[0]
        
        # If table doesn't exist, create it
        if not exists:
            print(f"Creating table for {ticker} in {schema}")
            
            # First, ensure schema exists
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            
            # Create table with proper structure: both datetime and date as TIMESTAMP
            create_table_query = f"""
            CREATE TABLE {schema}.{ticker_lower} (
                datetime TIMESTAMP PRIMARY KEY, -- Primary timestamp key
                date TIMESTAMP,             -- Second timestamp column (no unique constraint)
                open NUMERIC(10, 5),
                high NUMERIC(10, 5),
                low NUMERIC(10, 5),
                close NUMERIC(10, 5),
                volume NUMERIC(14, 2),
                average NUMERIC(10, 5),
                barcount INTEGER
            )
            """
            cursor.execute(create_table_query)
            
            # Create index on the second timestamp column (date) for potential queries
            # Note: No unique constraint here!
            cursor.execute(f"CREATE INDEX idx_{ticker_lower}_date ON {schema}.{ticker_lower} (date)")
            
            conn.commit()
            print(f"Created table and indices for {ticker} with 'date' as TIMESTAMP")
            exists = True
        # If table *does* exist, check schema and fix if needed
        else:
            print(f"Table {schema}.{ticker_lower} exists. Verifying schema...")
            schema_ok = True
            needs_commit = False
            
            # 1. Check and fix data type of 'date' column (should be TIMESTAMP)
            check_type_query = f"""
            SELECT data_type 
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
              AND table_name = '{ticker_lower}'
              AND column_name = 'date'
            """
            cursor.execute(check_type_query)
            result = cursor.fetchone()
            if result and result[0].lower() == 'date': # Check if it is incorrectly DATE
                print(f"  Column 'date' in {ticker_lower} has incorrect type 'DATE'. Attempting to change to TIMESTAMP...")
                try:
                    # Attempt to change type - this might require casting if data exists
                    # If data exists, a simple TYPE change might fail. Using ::timestamp assumes existing data is castable.
                    alter_type_query = f"ALTER TABLE {schema}.{ticker_lower} ALTER COLUMN date TYPE TIMESTAMP USING date::timestamp;"
                    cursor.execute(alter_type_query)
                    print(f"  Successfully changed 'date' column type to TIMESTAMP for {ticker}")
                    needs_commit = True 
                except Exception as type_err:
                    print(f"  Error changing 'date' column type to TIMESTAMP for {ticker}: {type_err}")
                    print(f"  Existing data might be incompatible. Manual intervention may be needed.")
                    schema_ok = False
            elif not result:
                 print(f"  Could not find 'date' column for {ticker_lower} to verify type.")
                 schema_ok = False # Cannot proceed if column missing
            elif result[0].lower().startswith('timestamp'):
                 print(f"  Column 'date' has correct type ('{result[0]}').")
            else: # Some other unexpected type
                 print(f"  Column 'date' has unexpected type '{result[0]}'. Manual check needed.")
                 schema_ok = False

            # 2. Check and drop unique constraint on 'date' column (if schema is still ok)
            if schema_ok:
                constraint_name = f"{ticker_lower}_date_key" # The potential problematic constraint name
                check_constraint_query = f"""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = '{schema}'
                  AND table_name = '{ticker_lower}'
                  AND constraint_name = '{constraint_name}'
                  AND constraint_type = 'UNIQUE'
                """
                cursor.execute(check_constraint_query)
                constraint_exists = cursor.fetchone()
                
                if constraint_exists:
                    print(f"  Found potentially conflicting unique constraint '{constraint_name}'. Attempting to drop...")
                    try:
                        drop_constraint_query = f"ALTER TABLE {schema}.{ticker_lower} DROP CONSTRAINT IF EXISTS {constraint_name}"
                        cursor.execute(drop_constraint_query)
                        print(f"  Successfully dropped constraint '{constraint_name}' for {ticker}")
                        needs_commit = True
                    except Exception as alter_err:
                        print(f"  Error dropping constraint '{constraint_name}' for {ticker}: {alter_err}")
                        schema_ok = False # Mark schema as not ok if constraint drop fails
                else:
                    print(f"  No unique constraint named '{constraint_name}' found on 'date' column.")
            
            # Commit all schema changes if everything was successful and changes were made
            if schema_ok and needs_commit:
                conn.commit()
                print(f"Schema fix committed for {ticker}.")
            elif schema_ok and not needs_commit:
                 print(f"Schema verified for {ticker}. No changes needed.")
            else:
                print(f"Schema issues found or fixing failed for {ticker}. Rolling back changes and skipping ticker.")
                conn.rollback() # Rollback any partial changes
                exists = False # Mark as failed
                
        cursor.close()
        conn.close()
        
        return exists # Return True only if table exists and schema is OK
        
    except Exception as e:
        print(f"Error ensuring table exists/schema is correct for {ticker}: {e}")
        # Ensure connection is closed on error
        if 'conn' in locals() and conn:
            try:
                conn.rollback() # Rollback on general error
                conn.close()
            except:
                pass
        return False

def verify_ticker_table_exists(ticker, ticker_location, db_config):
    """
    Verify that the ticker table exists in the database.
    
    Args:
        ticker (str): Ticker symbol
        ticker_location (dict): Dictionary with database location info
        db_config (dict): Database configuration
        
    Returns:
        bool: True if the table exists, False otherwise
    """
    try:
        # Connect to database
        config = db_config.copy()
        config['dbname'] = ticker_location['database']
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Check if table exists
        ticker_lower = ticker.lower()
        query = f"""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = '{ticker_location['schema']}' 
            AND table_name = '{ticker_lower}'
        )
        """
        
        cursor.execute(query)
        exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return exists
        
    except Exception as e:
        print(f"Error checking if table exists for {ticker}: {e}")
        return False

def insert_data_to_db(ticker_location, ticker, df, db_config):
    """
    Insert OHLC data into the database using execute_values for faster bulk insertion.
    Ensures both 'datetime' and 'date' columns receive the full timestamp.
    Handles conflicts on the 'datetime' primary key by ignoring duplicates.

    Args:
        ticker_location (dict): Dictionary with database location info
        ticker (str): Ticker symbol
        df (DataFrame): OHLC data to insert (must contain 'datetime' column)
        db_config (dict): Database configuration

    Returns:
        bool: True if successful, False otherwise
    """
    if df is None or df.empty:
        print(f"No data provided to insert for {ticker}")
        return True # Return True as there's nothing to fail on

    # Ensure the required datetime column exists
    if 'datetime' not in df.columns:
        print(f"DataFrame missing required 'datetime' column for {ticker}")
        return False

    start_time = time.time()
    original_row_count = len(df)

    try:
        # Connect to database
        conn_config = db_config.copy() # Use a copy to avoid modifying original dict
        conn_config['dbname'] = ticker_location['database']
        conn = psycopg2.connect(**conn_config)
        cursor = conn.cursor()

        ticker_lower = ticker.lower()
        schema = ticker_location['schema']
        table_name = f"{schema}.{ticker_lower}"

        # Prepare data for insertion
        # Ensure barCount exists and handle NaNs
        if 'barCount' not in df.columns:
            df['barCount'] = 0
        df['barCount'] = df['barCount'].fillna(0).astype(int) # Ensure integer type

        # Define the exact columns expected by the database table in order
        db_columns = ['datetime', 'date', 'open', 'high', 'low', 'close', 'volume', 'average', 'barCount']
        column_str = ', '.join(db_columns)

        # Create list of tuples for insertion, ensuring correct order
        # Use .get() with default None for safety, though IB data usually has these
        data_tuples = [
            (
                row.datetime, # datetime column
                row.datetime, # date column (same value)
                row.open if pd.notna(row.open) else None,
                row.high if pd.notna(row.high) else None,
                row.low if pd.notna(row.low) else None,
                row.close if pd.notna(row.close) else None,
                row.volume if pd.notna(row.volume) else None,
                row.average if pd.notna(row.average) else None,
                int(row.barCount) # Ensure barCount is int
            )
            for row in df.itertuples(index=False) # Use itertuples for efficiency
        ]

        # Insert using ON CONFLICT (datetime) DO NOTHING
        # This lets the DB handle duplicate timestamps gracefully
        insert_query = f"""
        INSERT INTO {table_name} ({column_str})
        VALUES %s
        ON CONFLICT (datetime) DO NOTHING
        """

        print(f"🚀 Starting bulk insert of {len(data_tuples)} rows for {ticker} using execute_values...")
        insert_start_time = time.time()

        # Execute bulk insert with execute_values
        execute_values(cursor, insert_query, data_tuples, page_size=1000)
        conn.commit() # Commit the transaction

        insert_end_time = time.time()
        insert_duration = insert_end_time - insert_start_time
        rows_processed = len(data_tuples) # Number of rows attempted

        cursor.close()
        conn.close()

        end_time = time.time()
        total_duration = end_time - start_time
        avg_rows_per_sec = rows_processed / insert_duration if insert_duration > 0 else 0

        # Note: We can't easily tell exactly how many rows were *newly* inserted vs ignored due to conflict.
        print(f"✅ Processed {rows_processed} rows for {ticker} in {insert_duration:.3f} seconds ({avg_rows_per_sec:.2f} rows/sec)")
        print(f"   (Total function time: {total_duration:.3f}s)")
        return True

    except Exception as e:
        end_time = time.time()
        print(f"❌ Error during bulk insert for {ticker}: {e}")
        # Attempt to rollback and close connection on error
        try:
            if conn and not conn.closed:
                conn.rollback()
        except Exception as rb_err:
             print(f"  Error during rollback: {rb_err}")
        finally:
             try:
                 if cursor and not cursor.closed:
                     cursor.close()
             except Exception as cur_err:
                 print(f"  Error closing cursor: {cur_err}")
             try:
                 if conn and not conn.closed:
                     conn.close()
             except Exception as con_err:
                 print(f"  Error closing connection: {con_err}")

        print(f"   (Failed insert took {end_time - start_time:.3f} seconds)")
        return False

def update_date_column_to_match_datetime(ticker_location, ticker, db_config):
    """
    Update the 'date' column values to match the 'datetime' column for all records.
    This fixes cases where date column has only the date part without the time information.
    
    Args:
        ticker_location (dict): Dictionary with database location info
        ticker (str): Ticker symbol
        db_config (dict): Database configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    start_time = time.time()
    
    try:
        # Connect to database
        config = db_config.copy()
        config['dbname'] = ticker_location['database']
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        ticker_lower = ticker.lower()
        schema = ticker_location['schema']
        
        # First check if there's any data at all
        check_query = f"""
        SELECT COUNT(*) FROM {schema}.{ticker_lower}
        """
        cursor.execute(check_query)
        count = cursor.fetchone()[0]
        
        # If no data exists, skip the update
        if count == 0:
            print(f"No existing data for {ticker}, skipping date column fix")
            cursor.close()
            conn.close()
            return True
        
        # Update date column to match datetime column
        update_query = f"""
        UPDATE {schema}.{ticker_lower}
        SET date = datetime
        WHERE date != datetime OR date IS NULL
        """
        
        cursor.execute(update_query)
        rows_updated = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        end_time = time.time()
        print(f"Updated {rows_updated} rows for {ticker} in {end_time - start_time:.3f} seconds")
        return True
        
    except Exception as e:
        end_time = time.time()
        print(f"Error updating date column for {ticker}: {e}")
        # Attempt to rollback and close connection on error
        try:
            if conn:
                conn.rollback()
        except:
            pass
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass
            
        print(f"Failed update took {end_time - start_time:.3f} seconds")
        return False

def update_all_tickers_data(fix_date_column=False, start_db=None, start_schema=None):
    """
    Main function to update OHLC data for all tickers listed in the prices schema file.

    Args:
        fix_date_column (bool, optional): Whether to fix date column values to match datetime. Default is False.
        start_db (str, optional): The database name to start processing from. Default is None (start from beginning).
        start_schema (str, optional): The schema name within start_db to start processing from. Default is None (start from beginning of start_db or beginning overall).
    """
    # Start timing the entire process
    total_start_time = time.time()

    # Get database configuration
    db_config = get_default_db_config()

    # Load prices schema data (or check if it was loaded successfully earlier)
    prices_schema_file = os.path.join('src', 'data', 'database_schemas_prices.json')
    try:
        with open(prices_schema_file, 'r') as f:
            prices_schema_data = json.load(f)
        print(f"Using prices schema from {prices_schema_file}")
    except Exception as e:
        print(f"Error loading prices schema file {prices_schema_file}: {e}")
        return # Cannot proceed without the schema

    # Connect to IB
    ib = get_ib()
    if not ib:
        print("Failed to connect to Interactive Brokers")
        return

    # Flag to control when to start processing based on start_db/start_schema
    start_processing = (start_db is None and start_schema is None)
    if not start_processing:
        print(f"Attempting to start processing from DB: '{start_db}', Schema: '{start_schema}'")

    try:
        # No longer need to build a flat list upfront
        # processing_tasks = []
        # ticker_locations = {}
        # processed_tickers = set()

        # Counters for summary
        total_tickers_processed = 0
        success_count = 0
        error_count = 0
        skipped_no_data_count = 0
        skipped_due_to_start_point = 0

        print("Starting ticker update process...")
        for db_name, schemas in prices_schema_data.items():
            # --- Start Point Logic (Database Level) ---
            if not start_processing and start_db is not None:
                if db_name == start_db:
                    # Reached the target database, now check schema or start processing
                    if start_schema is None:
                        print(f"--> Reached start database '{db_name}'. Starting processing.")
                        start_processing = True
                    # else: We need to find the specific schema within this DB
                else:
                    print(f"Skipping database '{db_name}' (before start point)...")
                    skipped_due_to_start_point += sum(len(ticker_list) for ticker_list in schemas.values() if isinstance(ticker_list, list)) # Estimate skipped tickers
                    continue # Skip this entire database

            # Check schema format
            if not isinstance(schemas, dict):
                print(f"Warning: Skipping database '{db_name}' due to unexpected format.")
                continue

            for schema_name, ticker_table_list in schemas.items():
                # --- Start Point Logic (Schema Level) ---
                if not start_processing: # This implies start_db was matched (or None) and start_schema is set
                    if start_schema is not None and schema_name == start_schema:
                        print(f"--> Reached start schema '{schema_name}' in database '{db_name}'. Starting processing.")
                        start_processing = True
                    else:
                        print(f"Skipping schema '{schema_name}' in db '{db_name}' (before start point)...")
                        if isinstance(ticker_table_list, list):
                             skipped_due_to_start_point += len(ticker_table_list)
                        continue # Skip this schema

                # Check ticker list format
                if not isinstance(ticker_table_list, list):
                    print(f"Warning: Skipping schema '{schema_name}' in db '{db_name}' due to unexpected format.")
                    continue

                # Print the header for the current database and schema being processed
                print(f"\n---> Updating: {db_name} / {schema_name} <---")

                if not ticker_table_list: # Check if the list of tickers is empty
                    print(f"  No tickers listed for this schema.")
                    continue

                # Process each ticker listed under this specific schema
                for ticker_table_name in ticker_table_list:
                    ticker_start_time = time.time()
                    # The table name is the lowercase ticker
                    ticker_upper = ticker_table_name.upper()
                    total_tickers_processed += 1 # Increment total counter

                    print(f"  Processing {ticker_upper}...") # Simple log for the ticker

                    try:
                        # Construct the ticker location info here
                        ticker_location = {
                            "database": db_name,
                            "schema": schema_name,
                            "ticker": ticker_upper # Keep original case for IB
                        }

                        # If fix_date_column flag is set, update date column to match datetime
                        if fix_date_column:
                            print(f"    Attempting to fix date column for {ticker_upper}...")
                            update_success = update_date_column_to_match_datetime(ticker_location, ticker_upper, db_config)
                            if update_success:
                                print(f"    Successfully checked/fixed date column for {ticker_upper}")
                            else:
                                print(f"    Failed to fix date column for {ticker_upper}. Skipping further processing.")
                                error_count += 1
                                continue # Skip to next ticker if date fix fails

                        # Get the last date of data
                        last_date = get_last_data_date(ticker_location, ticker_upper, db_config)

                        # If no existing data, skip update.
                        if not last_date:
                            print(f"    No existing data found for {ticker_upper}. Skipping update.")
                            skipped_no_data_count += 1
                            continue

                        # Calculate start date for fetching new data
                        start_date = last_date + timedelta(minutes=1)
                        print(f"    Last data: {last_date}. Requesting new data since {start_date}")

                        # Get data from IB
                        df = get_stock_data_from_ib(ib, ticker_upper, start_date)

                        if df is not None and not df.empty:
                            print(f"    Received {len(df)} new bar(s). Inserting into DB...")
                            success = insert_data_to_db(ticker_location, ticker_upper, df, db_config)
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                print(f"    Error inserting data for {ticker_upper}.")
                        elif df is None:
                             print(f"    Error retrieving data from IB for {ticker_upper}. Check logs.")
                             error_count += 1
                        else: # df is empty
                            print(f"    No new data available from IB for {ticker_upper} since {start_date}.")
                            success_count += 1  # Count as success if no new data

                    except Exception as e:
                        print(f"    Error processing {ticker_upper}: {e}")
                        import traceback
                        traceback.print_exc()
                        error_count += 1
                    finally:
                        ticker_end_time = time.time()
                        print(f"    Processing time for {ticker_upper}: {ticker_end_time - ticker_start_time:.3f} seconds")
                        # Removed the separator line here to reduce clutter, header provides separation

        # Final Summary
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time

        print(f"\nUpdate completed in {total_duration:.3f} seconds")
        print(f"Summary: Processed {total_tickers_processed} tickers.")
        print(f"         {success_count} successful updates/checks, {error_count} errors, {skipped_no_data_count} skipped (no prior data).")
        if skipped_due_to_start_point > 0:
             print(f"         Skipped approximately {skipped_due_to_start_point} tickers before reaching start point.")
        if total_tickers_processed > 0:
             print(f"Average time per ticker processed: {total_duration / total_tickers_processed:.3f} seconds")

    finally:
        # Disconnect from IB
        if ib and ib.isConnected():
            ib.disconnect()
            print("Disconnected from Interactive Brokers")

if __name__ == "__main__":
    db_to_start = "equity_sector_communication_services_prices"
    schema_to_start = "diversified_telecommunication_services_prices"
    print(f"\nStarting update from DB: {db_to_start}, Schema: {schema_to_start}\n")
    update_all_tickers_data(fix_date_column=False, start_db=db_to_start, start_schema=schema_to_start)




