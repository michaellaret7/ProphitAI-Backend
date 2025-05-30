import psycopg2
import os
from dotenv import load_dotenv
import math
import re # Import re for snake_case conversion
from src.utils.database import get_default_db_config, get_cursor # Import get_cursor

# Assuming this is the correct path - might need adjustment
try:
    # TODO: Verify this import path is correct for your project structure
    from src.utils.file_utils import load_schema_data
except ImportError:
    # # print("Error: Could not import 'load_schema_data' from 'src.utils.file_utils'. Ensure the file exists and is in the Python path.")
    # Define a dummy function or raise an error to prevent proceeding
    def load_schema_data():
        raise ImportError("Dummy function: load_schema_data unavailable. Cannot determine DB/Schema for ticker.")

# Load environment variables from .env file if it exists
load_dotenv()

# Database Credentials from Environment Variables
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")

def _get_db_and_schema_for_ticker(ticker: str) -> tuple[str | None, str | None]:
    """
    Finds the database name and schema name for a given ticker using schema data.

    Args:
        ticker (str): The stock ticker symbol.

    Returns:
        tuple[str | None, str | None]: A tuple containing (database_name, schema_name),
                                       or (None, None) if not found or on error.
    """
    ticker_upper = ticker.upper()
    try:
        # Load the schema configuration which maps sectors/schemas/tickers
        # Expects a structure like:
        # { "sector_key": { "db_name": "...", "schemas": { "schema_name": { "tables": { ... "tickers": [...] ... } } } } }
        all_sector_data = load_schema_data()
        if not all_sector_data:
            #  # print("Error: Schema data loaded is empty.")
             return None, None

        for sector_key, sector_info in all_sector_data.items():
            # Determine DB name: Prefer explicit 'db_name', fallback to pattern
            db_name = sector_info.get("db_name")
            if not db_name:
                # If db_name is not explicitly defined, assume sector_key already contains
                # the necessary prefix (e.g., "equity_sector_information_technology")
                # and just append the suffix.
                db_name = f"{sector_key}_fundamentals" # Corrected fallback pattern

            schemas = sector_info.get('schemas', {})
            for schema_name, schema_data in schemas.items():
                # Skip 'public' schema if it exists at this level
                if schema_name.lower() == 'public':
                    continue
                # Iterate through table categories (e.g., balance_sheets, financial_metrics)
                for table_category, tables_in_category in schema_data.get('tables', {}).items():
                    # Check tickers associated with this category/schema
                    for t in tables_in_category.get('tickers', []):
                        if str(t).upper() == ticker_upper:
                            # Found the ticker, return its db and schema
                            return db_name, schema_name

    except ImportError:
         # Raised if the dummy load_schema_data function was used
        #  # print("Error: load_schema_data function is not available.")
         return None, None
    except FileNotFoundError:
        # # print("Error: Schema configuration file not found by load_schema_data.")
        return None, None
    except Exception as e:
        # Catch other potential errors during loading/parsing (e.g., JSON errors)
        # # print(f"Error loading or parsing schema data: {e}")
        return None, None

    # Ticker was not found in any schema
    # # print(f"Ticker '{ticker_upper}' not found in the schema configuration.")
    return None, None

def _sanitize_metric_value(value) -> float | None:
    """Basic sanitization for numeric metric values, handling None, NaN, Inf."""
    if value is None:
        return None
    try:
        val = float(value)
        # Allow negative values, but exclude NaN/Inf
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        # Value couldn't be converted to float
        return None

def _metric_name_to_column_name(metric_name: str) -> str:
    """
    Converts a user-friendly metric name (e.g., "Price to Earnings Ratio")
    to a likely database column name (e.g., "price_to_earnings_ratio").
    Handles spaces, dashes, slashes, and basic capitalization.
    """
    # Convert to lowercase first
    name = metric_name.lower()
    # Replace common separators with underscores
    name = name.replace(' ', '_').replace('-', '_').replace('/', '_')
    # Remove any resulting multiple underscores
    name = re.sub('_+', '_', name)
    # Remove potential leading/trailing underscores from replacements
    return name.strip('_')


def retrieve_financial_metric(ticker: str, metric_name: str) -> list[tuple[object, float]] | None:
    """
    Retrieves the time series of a specified financial metric for a given stock ticker
    from the relevant sector database and financial_metrics table.

    It attempts to fetch the metric values along with a date column, ordered by date.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL'). Case-insensitive.
        metric_name (str): The user-friendly name of the financial metric to retrieve
                           (e.g., "Price to Earnings Ratio", "Revenue", "Net Income").
                           This will be converted to a potential column name.

    Returns:
        list[tuple[object, float]] | None: A list of (date, metric_value) tuples if found and valid,
                                         ordered by date (if a date column is found).
                                         Returns None if connection fails, ticker/table/column not found,
                                         or other critical errors occur.
                                         Returns an empty list if the table is empty or contains no valid data for the metric.
    """
    if not ticker:
        # # print("Error: Ticker symbol cannot be empty.")
        return None
    if not metric_name:
        # # print("Error: Metric name cannot be empty.")
        return None

    db_config = get_default_db_config()
    if not all(db_config.values()):
        print("DEBUG: DB Credentials MISSING or INCOMPLETE in environment.")
        return None
        
    ticker = ticker.strip().upper()
    column_name = _metric_name_to_column_name(metric_name)

    db_name, schema_name = _get_db_and_schema_for_ticker(ticker)
    if not db_name or not schema_name:
        print(f"DEBUG: Failed to find DB/Schema for ticker '{ticker}'.")
        return None

    table_name = f"{ticker.lower()}_financial_metrics"
    all_metric_values = []

    try:
        with get_cursor(db_name, db_config) as cur: # Use context manager
            # --- Determine available date column ---
            date_column_to_use = None
            potential_date_columns = ['date', 'period', 'filing_date', 'report_date']
            for col_name_check in potential_date_columns:
                check_date_col_query = """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s AND column_name = %s
                );
                """
                cur.execute(check_date_col_query, (schema_name, table_name, col_name_check))
                if cur.fetchone()[0]:
                    date_column_to_use = col_name_check
                    break
            
            # --- Check if Metric Column Exists ---
            check_metric_col_query = """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                  AND column_name = %s
            );
            """
            cur.execute(check_metric_col_query, (schema_name, table_name, column_name))
            metric_column_exists = cur.fetchone()[0]

            if not metric_column_exists:
                check_table_exists_query = """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                );
                """
                cur.execute(check_table_exists_query, (schema_name, table_name))
                if not cur.fetchone()[0]:
                    print(f"DEBUG: Table '{schema_name}.{table_name}' does not exist. Returning None.")
                    return None
                else:
                    print(f"DEBUG: Column '{column_name}' does not exist in table '{schema_name}.{table_name}'. Returning None.")
                    return None

            # --- Construct Data Query ---
            from psycopg2 import sql
            select_clause = f'"{column_name}"'
            if date_column_to_use:
                select_clause = f'"{date_column_to_use}", {select_clause}'

            query = sql.SQL('SELECT {select_fields} FROM {schema}.{table}').format(
                select_fields=sql.SQL(select_clause),
                schema=sql.Identifier(schema_name),
                table=sql.Identifier(table_name)
            )

            if date_column_to_use:
                query = sql.SQL('{query} ORDER BY {date_col} ASC').format(
                    query=query,
                    date_col=sql.Identifier(date_column_to_use)
                )
            
            cur.execute(query)
            results = cur.fetchall()

            if results:
                for row in results:
                    metric_value = None
                    date_value = None
                    if date_column_to_use:
                        date_value = row[0]
                        metric_value = _sanitize_metric_value(row[1])
                    else:
                        metric_value = _sanitize_metric_value(row[0])

                    if metric_value is not None:
                        all_metric_values.append((date_value, metric_value))
    
    except psycopg2.errors.UndefinedTable:
        print(f"DEBUG: Caught UndefinedTable error for '{schema_name}'.'{table_name}'.")
        return None
    except psycopg2.errors.UndefinedColumn:
         print(f"DEBUG: Caught UndefinedColumn error for column '{column_name}' in '{schema_name}'.'{table_name}'.")
         return None
    except psycopg2.OperationalError as e:
        print(f"DEBUG: Caught OperationalError: {e}")
        return None
    except psycopg2.Error as e: # Catch-all for other psycopg2 errors
        print(f"DEBUG: Caught other psycopg2.Error: {e}")
        return None
    except ImportError as e: # Handle dummy load_schema_data case
        print(f"DEBUG: Caught ImportError: {e}")
        return None
    except Exception as e: # Catch any other unexpected Python errors
        print(f"DEBUG: Caught unexpected Exception: {e}")
        return None

    return all_metric_values

# # --- Example Usage Block ---
# if __name__ == "__main__":
#     # This block executes only when the script is run directly
#     # Useful for testing the function.

#     # Ensure .env file is in the correct location relative to script execution
#     # or that environment variables are set system-wide.
#     # # print("Loading environment variables for direct script execution...")
#     load_dotenv() # Load again ensures it works if run directly vs imported

#     # Test cases
#     test_ticker = "AAPL"
#     test_metrics = ["Price to Earnings Ratio", "free cash flow growth"]

#     for metric in test_metrics:
#         # print(f"\n--- Testing: Ticker={test_ticker}, Metric='{metric}' ---")
#         data = retrieve_financial_metric(test_ticker, metric)
#         print(data)
#         if data is None:
#             # print("Result: Function returned None (Indicates an error occurred).")
#             pass
#         elif not data:
#             # print("Result: Function returned an empty list (No valid data found).")
#             pass
#         else:
#             # print(f"Result: Retrieved {len(data)} data points.")
#             # print("First 5 entries:")
#             for i, (date_val, metric_val) in enumerate(data[:5]):
#                 date_str = str(date_val) if date_val else "N/A"
#                 # print(f"  {i+1}. Date: {date_str}, Value: {metric_val:.2f}")
#             if len(data) > 5:
#                  # print("  ...")
#                  pass

