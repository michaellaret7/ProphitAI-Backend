#!/usr/bin/env python
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
schema_data = load_schema_data()

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
    Insert OHLC data into the database using batched INSERT ON CONFLICT.
    Ensures both 'datetime' and 'date' columns receive the full timestamp.
    
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
        db_config['dbname'] = ticker_location['database']
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        ticker_lower = ticker.lower()
        schema = ticker_location['schema']
        
        # Prepare data for insertion
        records = []
        
        # Ensure barCount exists and handle NaNs
        if 'barCount' not in df.columns:
            df['barCount'] = 0
        df['barCount'] = df['barCount'].fillna(0).astype(int)
        
        # Define the columns expected by the database table
        db_columns = ['datetime', 'date', 'open', 'high', 'low', 'close', 'volume', 'average', 'barCount']
        
        # Create list of tuples for insertion
        # Insert the same timestamp into both 'datetime' and 'date' columns
        for row_tuple in df.itertuples(index=False):
            record_dict = row_tuple._asdict() # Convert named tuple to dict
            record = (
                record_dict['datetime'], # For datetime column
                record_dict['datetime'], # For date column (using the same timestamp)
                record_dict.get('open', None),
                record_dict.get('high', None),
                record_dict.get('low', None),
                record_dict.get('close', None),
                record_dict.get('volume', None),
                record_dict.get('average', None),
                record_dict.get('barCount', 0)
            )
            records.append(record)
            
        # Insert using ON CONFLICT (datetime) DO NOTHING
        # This lets the DB handle duplicate timestamps gracefully
        insert_query = f"""
        INSERT INTO {schema}.{ticker_lower}
        (datetime, date, open, high, low, close, volume, average, barcount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (datetime) DO NOTHING
        """
        
        # Execute in batches for better performance
        batch_size = 1000
        rows_processed = 0
        
        print(f"Starting batched insert of {len(records)} rows for {ticker} with ON CONFLICT...")
        insert_start_time = time.time()
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            if not batch:
                continue
            
            # executemany returns None, so we can't easily get exact inserted count
            cursor.executemany(insert_query, batch)
            conn.commit()
            rows_processed += len(batch)
            # Print progress periodically if desired
            # if (i // batch_size) % 10 == 0: 
            #     print(f"  Processed {rows_processed}/{len(records)}...")

        insert_end_time = time.time()
            
        cursor.close()
        conn.close()
        
        end_time = time.time()
        # Note: We can't easily tell exactly how many rows were *newly* inserted vs ignored due to conflict.
        # We report the number of rows processed.
        print(f"Processed {rows_processed} rows for {ticker} in {insert_end_time - insert_start_time:.3f} seconds (Total function time: {end_time - start_time:.3f}s)")
        return True
        
    except Exception as e:
        end_time = time.time()
        print(f"Error during batched insert for {ticker}: {e}")
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
            
        print(f"Failed insert took {end_time - start_time:.3f} seconds")
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

def update_all_tickers_data(target_sector=None, target_schema=None, target_table=None, fix_date_column=False):
    """
    Main function to update OHLC data for tickers in the database.
    Can be limited to a specific subindustry by providing sector, schema, and table.
    
    Args:
        target_sector (str, optional): Specific sector to process. Default is None (all sectors).
        target_schema (str, optional): Specific schema to process. Default is None (all schemas).
        target_table (str, optional): Specific table (subindustry) to process. Default is None (all tables).
        fix_date_column (bool, optional): Whether to fix date column values to match datetime. Default is False.
    """
    # Start timing the entire process
    total_start_time = time.time()
    
    # Get database configuration
    db_config = get_default_db_config()
    
    # Load schema data
    schema_data = load_schema_data()
    
    # Connect to IB
    ib = get_ib()
    if not ib:
        print("Failed to connect to Interactive Brokers")
        return
        
    try:
        # Extract all tickers from schema
        tickers = []
        ticker_locations = {}
        
        # If targeting a specific subindustry
        if target_sector and target_schema and target_table:
            print(f"Processing only tickers from: {target_sector} -> {target_schema} -> {target_table}")
            
            # Remove "_prices" suffix from target names to match the schema_data keys
            sector_key = target_sector.replace("_prices", "")
            schema_key = target_schema.replace("_prices", "")
            table_key = target_table.replace("_prices", "")
            
            # Check if the specified target exists
            if sector_key in schema_data:
                sector_info = schema_data[sector_key]
                database = sector_info.get('database')
                schemas = sector_info.get('schemas', {})
                
                if schema_key in schemas:
                    schema_info = schemas[schema_key]
                    tables = schema_info.get('tables', {})
                    
                    if table_key in tables:
                        table_info = tables[table_key]
                        table_tickers = table_info.get('tickers', [])
                        
                        for ticker in table_tickers:
                            # Determine the database name based on sector name
                            if "etf" in sector_key.lower():
                                db_name = "etf_prices"
                            else:
                                db_name = f"{database}_prices"
                                
                            ticker_location = {
                                "database": db_name,
                                "schema": f"{schema_key}_prices",
                                "ticker": ticker
                            }
                            
                            # Instead of ensuring/creating table, check if it already exists
                            if verify_ticker_table_exists(ticker, ticker_location, db_config):
                                tickers.append(ticker)
                                ticker_locations[ticker] = ticker_location
                            else:
                                print(f"Skipping {ticker} - table doesn't exist and we won't create it")
                    else:
                        print(f"Table '{table_key}' not found in schema '{schema_key}'")
                else:
                    print(f"Schema '{schema_key}' not found in sector '{sector_key}'")
            else:
                print(f"Sector '{sector_key}' not found in schema data")
        # If no specific target, process everything or first subindustry
        else:
            # Or process the first subindustry if no specific targets provided
            first_subindustry_found = False
            
            for sector_name, sector_info in schema_data.items():
                if target_sector and sector_name != target_sector.replace("_prices", ""):
                    continue
                    
                database = sector_info.get('database')
                schemas = sector_info.get('schemas', {})
                
                for schema_name, schema_info in schemas.items():
                    if target_schema and schema_name != target_schema.replace("_prices", ""):
                        continue
                        
                    tables = schema_info.get('tables', {})
                    
                    for table_name, table_info in tables.items():
                        if target_table and table_name != target_table.replace("_prices", ""):
                            continue
                            
                        table_tickers = table_info.get('tickers', [])
                        
                        for ticker in table_tickers:
                            # Determine the database name based on sector name
                            if "etf" in sector_name.lower():
                                db_name = "etf_prices"
                            else:
                                db_name = f"{database}_prices"
                                
                            ticker_location = {
                                "database": db_name,
                                "schema": f"{schema_name}_prices",
                                "ticker": ticker
                            }
                            
                            # Instead of ensuring/creating table, check if it already exists
                            if verify_ticker_table_exists(ticker, ticker_location, db_config):
                                tickers.append(ticker)
                                ticker_locations[ticker] = ticker_location
                            else:
                                print(f"Skipping {ticker} - table doesn't exist and we won't create it")
                        
                        # If we're just looking for the first subindustry with no specific target
                        if not (target_sector or target_schema or target_table) and not first_subindustry_found and tickers:  # Use tickers not table_tickers
                            print(f"Testing with first sub-industry: {sector_name} -> {schema_name} -> {table_name}")
                            print(f"Found {len(tickers)} valid tickers in this sub-industry")
                            first_subindustry_found = True
                            # Break to only process the first table found
                            break
                    
                    # If processing only the first subindustry, break after the first one with tickers
                    if not (target_sector or target_schema or target_table) and first_subindustry_found:
                        break
                
                # If processing only the first subindustry, break after the first one with tickers
                if not (target_sector or target_schema or target_table) and first_subindustry_found:
                    break
        
        if not tickers:
            print("No valid tickers found to process")
            return
            
        print(f"Found {len(tickers)} valid tickers to update")
        
        # Update each ticker
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, ticker in enumerate(tickers):
            ticker_start_time = time.time()
            print(f"[{i+1}/{len(tickers)}] Processing {ticker}...")
            
            try:
                # Get the ticker location
                ticker_location = ticker_locations.get(ticker)
                if not ticker_location:
                    print(f"Could not find database location for {ticker}")
                    error_count += 1
                    continue
                
                # If fix_date_column flag is set, update date column to match datetime
                if fix_date_column:
                    print(f"Fixing date column for {ticker} to match datetime column...")
                    update_success = update_date_column_to_match_datetime(ticker_location, ticker, db_config)
                    if update_success:
                        print(f"Successfully fixed date column for {ticker}")
                    else:
                        print(f"Failed to fix date column for {ticker}")
                        error_count += 1
                        continue
                    
                # Get the last date of data
                last_date = get_last_data_date(ticker_location, ticker, db_config)
                
                # Skip tickers that don't have any existing data
                if not last_date:
                    print(f"No existing data for {ticker}, skipping this ticker")
                    skipped_count += 1
                    continue
                
                # If we have data, add 1 minute to get only new data
                start_date = last_date + timedelta(minutes=1)
                print(f"Last data for {ticker} is from {last_date}, getting data since {start_date}")
                
                # Get data from IB
                df = get_stock_data_from_ib(ib, ticker, start_date)
                
                if df is not None and not df.empty:
                    # Insert new data into database
                    success = insert_data_to_db(ticker_location, ticker, df, db_config)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    print(f"No new data available for {ticker}")
                    success_count += 1  # Count as success if no new data is normal
                
                ticker_end_time = time.time()
                print(f"Total processing time for {ticker}: {ticker_end_time - ticker_start_time:.3f} seconds")
                print("-" * 80)
                
            except Exception as e:
                ticker_end_time = time.time()
                print(f"Error processing {ticker}: {e}")
                print(f"Failed processing took {ticker_end_time - ticker_start_time:.3f} seconds")
                print("-" * 80)
                error_count += 1
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        print(f"\nUpdate completed in {total_duration:.3f} seconds")
        print(f"{success_count} tickers updated successfully, {error_count} errors, {skipped_count} skipped (no existing data)")
        print(f"Average time per ticker: {total_duration / len(tickers):.3f} seconds")
        
    finally:
        # Disconnect from IB
        if ib and ib.isConnected():
            ib.disconnect()
            print("Disconnected from Interactive Brokers")

if __name__ == "__main__":    
    # Or continue with regular updates:
    update_all_tickers_data("equity_sector_real_estate_prices", "industrial_reits_prices")
    
    
    
