"""
Author: @Michael Laret
=====================================================================
This file contains the functions for the fundamental analysis.
It queries the pre generated fundamental report from the database.
"""
import os
import json
import numpy as np
import psycopg2 # Added for PostgreSQL interaction
from psycopg2 import sql # Added for safe SQL query construction
from backend.src.utils.caching import cache_result
# Import utility functions for DB config and schema loading
from backend.src.utils.database import get_default_db_config
from backend.src.utils.file_utils import load_schema_data

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REPORT_COLUMN_NAME = os.environ.get("DB_REPORT_COLUMN", "report_text") # Keep this for flexibility

# Re-export the analysis generator so callers can simply import it from
# phase_two.retrieve_fundamental_report (keeps backward-compatibility with
# phase_two.__init__).
from backend.src.data.fundamental_report.generate_fundamental_report import (
    generate_fundamental_analysis_report as _generate_fundamental_analysis_report,
)

# Public alias with the expected name
generate_fundamental_analysis_report = _generate_fundamental_analysis_report

def get_fundamental_report_from_db(ticker):
    """
    Retrieve fundamental report for a ticker from PostgreSQL database.
    
    Uses schema lookup logic to locate the correct database and table,
    then fetches the stored fundamental analysis report content.
    
    Args:
        ticker: The stock ticker symbol to retrieve report for.
        
    Returns:
        str or None: The report content as string if found, None if not found
        or if connection/table errors occur.
    """
    conn = None
    cursor = None
    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()
    # Removed table_name construction from here, moved after schema lookup
    # table_name = f"{ticker_lower}_fundamental_report"

    # --- Schema Lookup Logic (adapted from data_retrieval.py/get_fundamentals_data) --- #
    schema_data = load_schema_data()
    if not schema_data:
        print("Error: Could not load database schema data.")
        return None

    ticker_location = None
    # Find ticker location based on fundamentals schema structure
    for sector_name, sector_info in schema_data.items():
        database = sector_info.get('database')
        schemas = sector_info.get('schemas', {})

        # Skip ETF data source for fundamental reports
        if "etf" in sector_name.lower():
             continue

        for schema_name, schema_info in schemas.items():
            tables = schema_info.get('tables', {})
            for table_name_in_schema, table_info in tables.items():
                tickers_in_table = table_info.get('tickers', [])
                # Case-insensitive check
                for db_ticker in tickers_in_table:
                    if ticker_upper == db_ticker.upper():
                        # Determine the correct database name for fundamentals
                        db_name = f"{database}_fundamentals"
                        ticker_location = {
                            "database": db_name,
                            "schema": schema_name, # Use the schema name directly
                            "ticker": db_ticker # Use the exact case ticker from schema
                        }
                        break
                if ticker_location: break
            if ticker_location: break
        if ticker_location: break

    if not ticker_location:
        print(f"Ticker {ticker_upper} not found in any database schema for fundamental reports.")
        return None
    # --- End Schema Lookup Logic --- #

    # Construct table name *after* schema lookup using the correct ticker case
    ticker_from_schema = ticker_location['ticker'] # Use the ticker case from schema for consistency elsewhere if needed
    # Force the ticker part of the table name to lowercase to match the database table naming convention
    table_name = f"{ticker_from_schema.lower()}_fundamental_report"

    # Get default DB configuration (host, user, pass, port)
    db_config = get_default_db_config()
    if not db_config or not all(k in db_config for k in ['host', 'user', 'password', 'port']):
        print("Default database configuration is incomplete. Check environment variables for get_default_db_config.")
        return None

    # Set the specific database name found via schema lookup
    db_config['dbname'] = ticker_location['database']
    schema_name = ticker_location['schema']

    # Removed the old check based on individual env vars
    # if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT]):
    #    print("Database environment variables (...) are not fully set.")
    #    return None

    try:
        # Establish database connection using the config dictionary
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Safely construct the SQL query including the schema
        # Reverted the WHERE clause addition from the previous incorrect attempt
        query = sql.SQL("SELECT {column} FROM {schema}.{table} LIMIT 1").format(
            column=sql.Identifier(REPORT_COLUMN_NAME),
            schema=sql.Identifier(schema_name), # Added schema identifier
            table=sql.Identifier(table_name)
        )

        # Execute the query
        # Reverted parameter passing from previous incorrect attempt
        cursor.execute(query)
        result = cursor.fetchone()

        # Return the report content if found
        if result:
            return result[0] # fetchone() returns a tuple, get the first element
        else:
            # Report not found in the table
            return None

    except psycopg2.Error as e:
        # Handle specific database errors (e.g., table not found, connection error)
        # Corrected error message to show the actual table name being queried
        print(f"Database error for ticker {ticker} querying table {schema_name}.{table_name}: {e}")
        # Check for 'table does not exist' error (common case)
        if "relation" in str(e) and "does not exist" in str(e):
             print(f"Table '{schema_name}.{table_name}' likely does not exist in database '{db_config['dbname']}'.")
        # Removed the specific column error check from the previous incorrect attempt
        # You might want more specific error handling or logging here
        return None
    except Exception as e:
        # Handle other unexpected errors
        print(f"An unexpected error occurred while fetching report for {ticker}: {e}")
        return None
    finally:
        # Ensure the connection is closed even if errors occur
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def debug_json_encoding(data, ticker):
    """
    Debug function to identify and fix JSON encoding issues.
    
    Analyzes data structure to find problematic fields causing JSON encoding
    failures and attempts to fix them by converting or replacing values.
    
    Args:
        data: List of dictionaries to encode and fix.
        ticker: Ticker symbol for logging purposes.
        
    Returns:
        Tuple[bool, str]: Success flag and either JSON string or error message.
    """
    # First try individual records
    for i, record in enumerate(data):
        try:
            json.dumps(record)
        except Exception as e:
            print(f"  Failed to encode record {i}: {e}")
            
            # Try each field individually
            for key, value in record.items():
                try:
                    json.dumps({key: value})
                except Exception as e:
                    print(f"    Problem field: '{key}' with value '{value}' (type: {type(value)}): {e}")
                    
                    # Try to fix this problematic field
                    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                        record[key] = None
                        print(f"      Fixed by replacing with None")
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        record[key] = str(value)
                        print(f"      Fixed by converting to string: '{record[key]}'")
                    else:
                        record[key] = None
                        print(f"      Fixed by replacing with None")
    
    # Try with fixed data
    try:
        json_str = json.dumps(data)
        print(f"  Final JSON encoding successful: {len(json_str)} bytes")
        return True, json_str
    except Exception as e:
        print(f"  Final JSON encoding still failed: {e}")
        return False, str(e)



