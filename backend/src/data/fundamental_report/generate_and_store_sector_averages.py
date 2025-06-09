"""
Author: @Michael Laret
=====================================================================
Connects to sector-specific databases (using env vars for credentials) to calculate
and store overall sector averages for specified financial metrics.

This stores the averages for each sector for given columns in the database. 
"""
import psycopg2
import json
from collections import defaultdict
import statistics
import os
from dotenv import load_dotenv
import math
from backend.src.utils.file_utils import load_schema_data

# Load environment variables
load_dotenv()

# --- Database Credentials (Keep outside function for simplicity for now) ---
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")

# --- Helper Sets / Thresholds ---
# Columns that are recorded as percentages and may be stored either as
# decimals (0.25) or whole-percent values (25).  If the absolute value is >1
# we assume it is stored as whole-percent and scale down by 100.
PERCENT_KEYWORDS = ("margin", "yield", "growth")

# Hard caps to drop obviously wrong outliers that would skew the median/mean
# Keep list short; adjust as needed.
MAX_ABS_VALUES = {
    "price_to_sales_ratio": 100,
    "price_to_earnings_ratio": 200,
    "peg_ratio": 1000,
}

def _sanitize_value(col_name, value):
    """
    Clean and normalize financial metric values for calculation.
    
    Removes NaN/Inf values, normalizes percentage columns, and clips outliers
    to prepare data for statistical calculations.
    
    Args:
        col_name: The name of the financial metric column.
        value: The raw value to sanitize.
        
    Returns:
        float or None: Cleaned float value or None if value should be ignored.
    """
    if value is None:
        return None
    try:
        val = float(value)
    except (ValueError, TypeError):
        return None

    # Remove NaN / Inf
    if math.isnan(val) or math.isinf(val):
        return None

    # Normalise percentage-like columns
    if any(k in col_name for k in PERCENT_KEYWORDS):
        if abs(val) > 1:  # likely stored as 25 instead of 0.25
            val = val / 100.0
        # still absurd after scaling? drop it
        if abs(val) > 5:  # >500 % probably bad
            return None

    # Outlier clipping for selected ratios
    max_abs = MAX_ABS_VALUES.get(col_name)
    if max_abs and abs(val) > max_abs:
        return None

    return val

# --- Helper Function ---
def calculate_average(values):
    """
    Calculate arithmetic mean of cleaned numeric values.
    
    Args:
        values: List of numeric values (already sanitized).
        
    Returns:
        float or None: The arithmetic mean or None if no valid values.
    """
    numeric_values = [float(v) for v in values if v is not None]
    if not numeric_values:
        return None
    return statistics.mean(numeric_values)

def trimmed_mean(values, proportion_to_cut=0.05):
    """
    Calculate trimmed mean by removing extreme values.
    
    Computes mean after dropping a proportion of the lowest and highest values
    to reduce impact of outliers.
    
    Args:
        values: List of numeric values to calculate trimmed mean for.
        proportion_to_cut: Proportion of extreme values to remove (default: 0.05).
        
    Returns:
        float or None: The trimmed mean or None if no valid values.
    """
    cleaned = sorted([v for v in values if v is not None])
    n = len(cleaned)
    if n == 0:
        return None
    k = int(n * proportion_to_cut)
    if k == 0:
        return statistics.mean(cleaned)
    trimmed = cleaned[k: n - k] if n - 2 * k > 0 else cleaned
    return statistics.mean(trimmed) if trimmed else statistics.mean(cleaned)

# --- Main Workflow Function ---
def calculate_and_store_sector_averages(db_name, target_schema_name, data_points_config):
    """
    Calculate sector-wide average fundamentals and store them in the database.
    
    Connects to a fundamentals database, processes all tickers to calculate
    sector-level averages for specified metrics, and stores results in a table.
    
    Args:
        db_name: The name of the fundamentals database to process.
        target_schema_name: The schema name to create/use for storing results.
        data_points_config: Dictionary defining columns to fetch per table type.
        
    Returns:
        None - Prints processing status and results to console.
    """
    print(f"--- Starting processing for database: {db_name} ---")
    
    # --- Load database schema --- 
    try:
        db_schemas_all = load_schema_data()
        
        # Dynamically find the correct key in the schema file
        # Assuming the key is db_name without '_fundamentals' suffix
        sector_key = db_name.replace("_fundamentals", "")
        if sector_key not in db_schemas_all:
             print(f"Error: Sector key '{sector_key}' not found in database_schemas.json.")
             return # Exit the function if sector key is invalid
        
        sector_schemas = db_schemas_all[sector_key].get('schemas', {})
        if not sector_schemas:
             print(f"Error: No schemas found for sector '{sector_key}' in database_schemas.json.")
             return
            
    except FileNotFoundError:
        print(f"Error: Schema file not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from database_schemas.json.")
        return
    except KeyError:
         print(f"Error: Could not find expected structure for '{sector_key}' in schema file.")
         return
    
    # --- Build Ticker-Schema Map ---
    ticker_schema_map = {}
    for schema_name, schema_data in sector_schemas.items():
        if schema_name.lower() == 'public': continue
        for table_category, tables_in_category in schema_data.get('tables', {}).items():
            for ticker in tables_in_category.get('tickers', []):
                ticker_upper = str(ticker).upper()
                if ticker_upper not in ticker_schema_map:
                    ticker_schema_map[ticker_upper] = schema_name

    tickers = sorted(list(ticker_schema_map.keys()))
    if not tickers:
        print(f"Warning: No tickers found for sector '{sector_key}'. Cannot proceed.")
        return
    print(f"Found {len(tickers)} tickers with associated schemas for {sector_key}.")

    # --- Initialize Data Structures ---
    ticker_averages = defaultdict(dict)
    all_values = defaultdict(list)
    conn = None
    cur = None

    # --- Main Processing Logic ---
    try:
        print(f"Connecting to database '{db_name}' on {DB_HOST}...")
        conn = psycopg2.connect(dbname=db_name, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        print("Connection successful.")

        # --- Data Fetching and Ticker Averaging ---
        for ticker in tickers:
            schema_name = ticker_schema_map.get(ticker)
            if not schema_name: continue # Should not happen

            print(f"Processing ticker: {ticker} (Schema: {schema_name})")
            ticker_data = {}
            has_data_for_ticker = False

            for table_type, requested_columns in data_points_config.items():
                table_name = f"{ticker.lower()}_{table_type}"

                # --- Check for existing columns before querying ---
                actual_columns_in_db = set()
                try:
                    info_query = """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s;
                    """
                    cur.execute(info_query, (schema_name, table_name))
                    results = cur.fetchall()
                    actual_columns_in_db = {row[0] for row in results}
                except psycopg2.Error as e:
                    # Likely table doesn't exist or other schema issue
                    conn.rollback() # Ensure transaction state is clean
                    # print(f"  WARNING: Could not get columns for {schema_name}.{table_name}: {e}") # Optional debug
                    continue # Skip this table_type for this ticker

                valid_columns_to_fetch = [col for col in requested_columns if col in actual_columns_in_db]
                
                if not valid_columns_to_fetch:
                    # print(f"  INFO: No requested columns found in {schema_name}.{table_name}. Skipping.") # Optional debug
                    continue # Skip if none of the requested columns exist in the DB table
                # --- End check ---

                # Query only the columns that actually exist
                column_str = ", ".join([f'\"{col}\"' for col in valid_columns_to_fetch]) 
                query = f'SELECT {column_str} FROM "{schema_name}"."{table_name}"'

                try:
                    # print(f"  DEBUG: Executing query: {query}") 
                    cur.execute(query)
                    results = cur.fetchall()
                    # print(f"  DEBUG: Raw results for {table_name}: {results}")

                    if results:
                        has_data_for_ticker = True
                        # Iterate using the list of columns we actually fetched
                        for i, col_name in enumerate(valid_columns_to_fetch):
                            sanitized_vals = []
                            for row_val in results:
                                cleaned = _sanitize_value(col_name, row_val[i])
                                if cleaned is not None:
                                    sanitized_vals.append(cleaned)
                            # print(f"    DEBUG: Clean values for {col_name}: {sanitized_vals}")
                            avg_val = calculate_average(sanitized_vals)
                            ticker_data[col_name] = avg_val
                            if avg_val is not None:
                                all_values[col_name].append(avg_val)
                
                except psycopg2.Error as e:
                    # Catch potential errors during data query execution (less likely for UndefinedColumn now)
                    # print(f"  DEBUG: Error executing query for \"{schema_name}\".\"{table_name}\": {e}")
                    conn.rollback()

            if has_data_for_ticker:
                ticker_averages[ticker] = ticker_data
        
        # --- Calculate Overall Averages ---
        overall_averages = {}
        print("\nCalculating overall averages across all tickers...")
        for metric, values_list in all_values.items():
            cleaned_vals = [v for v in values_list if v is not None]
            avg = trimmed_mean(cleaned_vals, 0.05) if cleaned_vals else None
            overall_averages[metric] = avg
            print(f"  Overall average for {metric}: {avg}")

        # --- Persist overall_averages to the database ---
        if overall_averages:
            print("\nPersisting overall averages to the database...")
            # Use the target_schema_name passed as argument
            new_table_name = "averages_table" # Keep table name consistent for this function

            try:
                print(f"  Ensuring schema '{target_schema_name}' exists...")
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS \"{target_schema_name}\"")
                conn.commit()
                print(f"  Schema '{target_schema_name}' ensured.")

                # Drop the table if it exists to ensure fresh schema
                print(f"  Dropping table '{target_schema_name}'.'{new_table_name}' if it exists...")
                cur.execute(f'DROP TABLE IF EXISTS "{target_schema_name}"."{new_table_name}" CASCADE') # Added CASCADE for dependencies
                print(f"  Table '{new_table_name}' dropped or did not exist.")

                print(f"  Creating table '{target_schema_name}'.'{new_table_name}'...")
                column_definitions = ["\"run_id\" SERIAL PRIMARY KEY"]
                for metric in overall_averages.keys():
                    column_definitions.append(f'\"{metric}\" FLOAT')
                
                create_table_sql = f"""CREATE TABLE IF NOT EXISTS "{target_schema_name}"."{new_table_name}" (
                    {', '.join(column_definitions)}
                );"""
                cur.execute(create_table_sql)
                conn.commit()
                print(f"  Table '{new_table_name}' ensured.")

                print(f"  Clearing existing data from '{new_table_name}'...")
                cur.execute(f'DELETE FROM "{target_schema_name}"."{new_table_name}"')
                print("  Existing data cleared.")

                print(f"  Inserting calculated averages into '{new_table_name}'...")
                column_names = [f'\"{col}\"' for col in overall_averages.keys()]
                value_placeholders = ", ".join(["%s"] * len(overall_averages))
                column_name_str = ", ".join(column_names)
                insert_sql = f'INSERT INTO "{target_schema_name}"."{new_table_name}" ({column_name_str}) VALUES ({value_placeholders})'
                insert_values = tuple(overall_averages.get(key) for key in overall_averages.keys())
                cur.execute(insert_sql, insert_values)
                conn.commit()
                print("  Successfully inserted overall averages.")

            except psycopg2.Error as db_err:
                print(f"  ERROR: Database error during persistence: {db_err}")
                conn.rollback()
            except Exception as persist_err:
                 print(f"  ERROR: An unexpected error occurred during persistence: {persist_err}")
                 conn.rollback()
        else:
            print("\nSkipping database persistence: No overall averages were calculated.")

    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("\nDatabase connection closed.")
    
    print(f"--- Finished processing for database: {db_name} ---")

# --- Main Execution Block ---
if __name__ == "__main__":
    TARGET_SCHEMA = "sector_averages"
    BASE_DB_NAME_PREFIX = "equity_sector_"
    BASE_DB_NAME_SUFFIX = "_fundamentals"

    SECTOR_CONFIGS = {
        "communication_services": {
            "db_suffix": "communication_services",
            "data_points": {
                "balance_sheets": ["total_debt"],
                "cash_flow_statements": ["net_cash_flow_from_operations", "capital_expenditure", "free_cash_flow"],
                "income_statements": ["revenue", "operating_income", "ebit"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "price_to_sales_ratio", "enterprise_value_to_ebitda_ratio",
                    "free_cash_flow_yield", "gross_margin", "operating_margin", "net_margin",
                    "return_on_equity", "return_on_assets", "asset_turnover", "working_capital_turnover",
                    "current_ratio", "debt_to_equity", "interest_coverage", "revenue_growth",
                    "earnings_per_share_growth", "free_cash_flow_growth", "earnings_per_share",
                    "free_cash_flow_per_share"
                ]
            }
        },
        "consumer_discretionary": {
            "db_suffix": "consumer_discretionary",
            "data_points": {
                "balance_sheets": ["total_debt"],
                "cash_flow_statements": ["net_cash_flow_from_operations", "capital_expenditure", "free_cash_flow"],
                "income_statements": ["revenue", "operating_income"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "price_to_sales_ratio", "enterprise_value_to_ebitda_ratio",
                    "free_cash_flow_yield", "gross_margin", "operating_margin", "net_margin",
                    "return_on_equity", "return_on_assets", "asset_turnover", "working_capital_turnover",
                    "current_ratio", "debt_to_equity", "interest_coverage", "revenue_growth",
                    "earnings_per_share_growth", "free_cash_flow_growth", "earnings_per_share",
                    "free_cash_flow_per_share", "return_on_invested_capital", "inventory_turnover", "days_sales_outstanding",
                    "operating_cycle", "quick_ratio", "payout_ratio"
                ]
            }
        },
        "consumer_staples": {
            "db_suffix": "consumer_staples",
            "data_points": {
                "balance_sheets": ["total_debt", "cash_and_equivalents"],
                "cash_flow_statements": ["net_cash_flow_from_operations", "capital_expenditure", "free_cash_flow"],
                "income_statements": ["revenue", "operating_income"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "price_to_sales_ratio", "enterprise_value_to_ebitda_ratio",
                    "free_cash_flow_yield", "gross_margin", "operating_margin", "net_margin",
                    "return_on_equity", "return_on_assets", "return_on_invested_capital",
                    "inventory_turnover", "days_sales_outstanding", "operating_cycle",
                    "working_capital_turnover", "current_ratio", "quick_ratio", "cash_ratio",
                    "operating_cash_flow_ratio", "debt_to_equity", "interest_coverage",
                    "revenue_growth", "free_cash_flow_growth", "earnings_per_share_growth",
                    "payout_ratio"
                ]
            }
        },
        "energy": {
            "db_suffix": "energy",
            "data_points": {
                "balance_sheets": [
                    "total_debt", "cash_and_equivalents", "property_plant_and_equipment", "shareholders_equity"
                ],
                "cash_flow_statements": [
                    "net_cash_flow_from_operations", "capital_expenditure", "free_cash_flow",
                    "net_cash_flow_from_investing", "dividends_and_other_cash_distributions"
                ],
                "income_statements": ["revenue", "operating_income", "interest_expense"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "price_to_book_ratio", "price_to_sales_ratio",
                    "enterprise_value_to_ebitda_ratio", "free_cash_flow_yield",
                    "gross_margin", "operating_margin", "net_margin",
                    "return_on_equity", "return_on_assets", "return_on_invested_capital",
                    "return_on_capital_employed", "asset_turnover",
                    "net_debt_to_ebitda", "debt_to_ebitda", "debt_to_equity",
                    "interest_coverage", "current_ratio", "quick_ratio", "cash_ratio",
                    "dividend_yield", "payout_ratio",
                    "revenue_growth", "earnings_growth", "free_cash_flow_growth", "ebitda_growth"
                ]
            }
        },
        "financials": {
            "db_suffix": "financials",
            "data_points": {
                "balance_sheets": [
                    "total_assets", "cash_and_equivalents", "trade_and_non_trade_receivables",
                    "deposit_liabilities", "shareholders_equity", "total_debt"
                ],
                "cash_flow_statements": [
                    "net_cash_flow_from_operations", "net_cash_flow_from_financing",
                    "dividends_and_other_cash_distributions", "free_cash_flow"
                ],
                "income_statements": ["revenue", "operating_income", "interest_expense", "net_income"],
                "financial_metrics": [
                    "price_to_book_ratio", "price_to_earnings_ratio",
                    "return_on_equity", "return_on_assets",
                    "net_margin", "operating_margin", "efficiency_ratio",
                    "debt_to_equity", "interest_coverage",
                    "current_ratio", "cash_ratio",
                    "revenue_growth", "earnings_growth",
                    "dividend_yield", "payout_ratio",
                    "free_cash_flow_yield"
                ]
            }
        },
        "health_care": {
            "db_suffix": "health_care",
            "data_points": {
                "balance_sheets": ["total_debt", "cash_and_equivalents", "goodwill_and_intangible_assets"],
                "cash_flow_statements": ["net_cash_flow_from_operations", "free_cash_flow"],
                "income_statements": ["revenue", "research_and_development", "operating_income"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "enterprise_value_to_ebitda_ratio", "free_cash_flow_yield",
                    "gross_margin", "operating_margin", "return_on_invested_capital",
                    "return_on_capital_employed", "net_debt_to_ebitda", "interest_coverage", "revenue_growth"
                ]
            }
        },
        "industrials": {
            "db_suffix": "industrials",
            "data_points": {
                "balance_sheets": [
                    "total_debt", "cash_and_equivalents", "property_plant_and_equipment", "inventory", "shareholders_equity"
                ],
                "cash_flow_statements": ["net_cash_flow_from_operations", "capital_expenditure", "free_cash_flow"],
                "income_statements": ["revenue", "operating_income"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "enterprise_value_to_ebitda_ratio", "free_cash_flow_yield",
                    "operating_margin", "ebitda_margin", "return_on_capital_employed", "return_on_assets",
                    "asset_turnover", "inventory_turnover", "net_debt_to_ebitda", "debt_to_equity",
                    "interest_coverage", "current_ratio", "quick_ratio", "revenue_growth"
                ]
            }
        },
        "information_technology": {
            "db_suffix": "information_technology",
            "data_points": {
                "balance_sheets": ["cash_and_equivalents", "total_debt", "goodwill_and_intangible_assets"],
                "cash_flow_statements": ["net_cash_flow_from_operations", "free_cash_flow"],
                "income_statements": ["revenue", "research_and_development", "operating_income"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "price_to_sales_ratio", "peg_ratio",
                    "free_cash_flow_yield", "gross_margin", "operating_margin", "net_margin",
                    "return_on_invested_capital", "revenue_growth", "earnings_per_share_growth", "cash_ratio"
                ]
            }
        },
        "materials": {
            "db_suffix": "materials",
            "data_points": {
                "balance_sheets": [
                    "total_debt", "cash_and_equivalents", "inventory", "property_plant_and_equipment", "shareholders_equity"
                ],
                "cash_flow_statements": ["net_cash_flow_from_operations", "capital_expenditure", "free_cash_flow"],
                "income_statements": ["revenue", "operating_income"],
                "financial_metrics": [
                    "price_to_book_ratio", "enterprise_value_to_ebitda_ratio", "free_cash_flow_yield",
                    "operating_margin", "ebitda_margin", "return_on_capital_employed", "return_on_assets",
                    "asset_turnover", "inventory_turnover", "net_debt_to_ebitda", "debt_to_equity",
                    "interest_coverage", "current_ratio", "quick_ratio", "revenue_growth"
                ]
            }
        },
        "real_estate": {
            "db_suffix": "real_estate",
            "data_points": {
                "balance_sheets": [
                    "total_debt", "cash_and_equivalents", "property_plant_and_equipment", "shareholders_equity"
                ],
                "cash_flow_statements": [
                    "net_cash_flow_from_operations", "free_cash_flow", "dividends_and_other_cash_distributions"
                ],
                "income_statements": ["revenue", "operating_income", "interest_expense"],
                "financial_metrics": [
                    "price_to_book_ratio", "enterprise_value_to_ebitda_ratio", "price_to_earnings_ratio",
                    "free_cash_flow_yield", "operating_margin", "net_margin", "return_on_equity",
                    "debt_to_equity", "net_debt_to_ebitda", "interest_coverage", "current_ratio",
                    "cash_ratio", "dividend_yield", "payout_ratio"
                ]
            }
        },
        "utilities": {
            "db_suffix": "utilities",
            "data_points": {
                "balance_sheets": [
                    "total_debt", "cash_and_equivalents", "property_plant_and_equipment", "shareholders_equity"
                ],
                "cash_flow_statements": [
                    "net_cash_flow_from_operations", "free_cash_flow", "dividends_and_other_cash_distributions"
                ],
                "income_statements": ["revenue", "operating_income", "interest_expense"],
                "financial_metrics": [
                    "price_to_earnings_ratio", "price_to_book_ratio", "enterprise_value_to_ebitda_ratio",
                    "free_cash_flow_yield", "operating_margin", "net_margin", "return_on_equity",
                    "debt_to_equity", "net_debt_to_ebitda", "interest_coverage", "current_ratio",
                    "dividend_yield", "payout_ratio", "revenue_growth"
                ]
            }
        }
    }

    for sector_name, config in SECTOR_CONFIGS.items():
        db_name = f"{BASE_DB_NAME_PREFIX}{config['db_suffix']}{BASE_DB_NAME_SUFFIX}"
        print(f"\n--- Processing Sector: {sector_name.replace('_', ' ').title()} ---")
        try:
            calculate_and_store_sector_averages(
                db_name=db_name,
                target_schema_name=TARGET_SCHEMA,
                data_points_config=config["data_points"]
            )
        except Exception as e:
            print(f"ERROR: Failed processing sector '{sector_name}'. Error: {e}")
            # Optionally, continue to the next sector or re-raise the exception
            # continue
    
    print("\n--- All Sector Processing Complete ---")




