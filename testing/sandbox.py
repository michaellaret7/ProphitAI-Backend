import psycopg2
import json
from collections import defaultdict
import statistics
import os

# --- Database Credentials (Keep outside function for simplicity for now) ---
DB_USER = "postgres"
DB_PASSWORD = "ml1710402!" # Be careful with hardcoding passwords
DB_HOST = "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"

# --- Configuration ---
# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the JSON file relative to the project root
project_root = os.path.dirname(script_dir)
json_file_path = os.path.join(project_root, 'src', 'data', 'database_schemas.json')

# --- Helper Function ---
def calculate_average(values):
    """Calculates the average of a list of values, attempting string conversion.

    Args:
        values: A list of values, potentially including strings representing numbers,
                numeric types, or None.

    Returns:
        The average as a float, or None if no valid numeric values are found.
    """
    numeric_values = []
    for v in values:
        if isinstance(v, (int, float)):
            numeric_values.append(float(v)) # Ensure consistency as float
        elif isinstance(v, str):
            try:
                # Attempt to convert string to float
                numeric_values.append(float(v))
            except ValueError:
                # Ignore strings that cannot be converted to float
                # print(f"  DEBUG: Could not convert string '{v}' to float.") # Optional debug
                pass
        # Ignore None and other non-convertible types

    if not numeric_values:
        return None
    return statistics.mean(numeric_values)


# --- Main Workflow Function ---
def calculate_and_store_sector_averages(db_name, target_schema_name, data_points_config):
    """Connects to a database, calculates sector averages, and stores them.

    Args:
        db_name (str): The name of the fundamentals database.
        target_schema_name (str): The name of the schema to create/use for storing results.
        data_points_config (dict): Dictionary defining columns to fetch per table type.
    """
    print(f"--- Starting processing for database: {db_name} ---")
    
    # --- Load database schema --- 
    try:
        with open(json_file_path, 'r') as f:
            db_schemas_all = json.load(f)
        
        # Dynamically find the correct key in the schema file
        # Assuming the key is db_name without '_fundamentals' suffix
        sector_key = db_name.replace("_fundamentals", "")
        if sector_key not in db_schemas_all:
             print(f"Error: Sector key '{sector_key}' not found in {json_file_path}.")
             return # Exit the function if sector key is invalid
        
        sector_schemas = db_schemas_all[sector_key].get('schemas', {})
        if not sector_schemas:
             print(f"Error: No schemas found for sector '{sector_key}' in {json_file_path}.")
             return
            
    except FileNotFoundError:
        print(f"Error: Schema file {json_file_path} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}.")
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

            for table_type, columns in data_points_config.items():
                table_name = f"{ticker.lower()}_{table_type}"
                column_str = ", ".join([f'"{col}"' for col in columns])
                query = f'SELECT {column_str} FROM "{schema_name}"."{table_name}"'

                try:
                    # print(f"  DEBUG: Executing query: {query}") # Keep debug prints commented unless needed
                    cur.execute(query)
                    results = cur.fetchall()
                    # print(f"  DEBUG: Raw results for {table_name}: {results}")

                    if results:
                        has_data_for_ticker = True
                        for i, col_name in enumerate(columns):
                            column_values = [row[i] for row in results if row[i] is not None]
                            # print(f"    DEBUG: Values for {col_name}: {column_values}")
                            avg_val = calculate_average(column_values)
                            ticker_data[col_name] = avg_val
                            if avg_val is not None:
                                all_values[col_name].append(avg_val)
                
                except psycopg2.Error as e:
                    # print(f"  DEBUG: Error executing query for \"{schema_name}\".\"{table_name}\": {e}")
                    conn.rollback()

            if has_data_for_ticker:
                ticker_averages[ticker] = ticker_data
        
        # --- Calculate Overall Averages ---
        overall_averages = {}
        print("\nCalculating overall averages across all tickers...")
        for metric, values_list in all_values.items():
            avg = calculate_average(values_list)
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

                print(f"  Ensuring table '{target_schema_name}'.'{new_table_name}' exists...")
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
        
        # --- Optional: Print Results --- 
        # print("\nTicker Averages:")
        # for ticker, averages in ticker_averages.items():
        #     print(f"  {ticker}: {averages}")

        # print("\nOverall Averages:")
        # print(overall_averages)

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
    # Define the data points specific to this run
    communication_services_data_points = {
        "balance_sheet": ["total_debt"],
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
    
    # Call the function for the Communication Services sector
    # calculate_and_store_sector_averages(
    #     db_name="equity_sector_communication_services_fundamentals", 
    #     target_schema_name="sector_averages", 
    #     data_points_config=communication_services_data_points
    # )

    consumer_discretionary_data_points = {
        "balance_sheet": ["total_debt"],
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
    
    calculate_and_store_sector_averages(
        db_name="equity_sector_consumer_discretionary_fundamentals",
        target_schema_name="sector_averages",
        data_points_config=consumer_discretionary_data_points
    )
