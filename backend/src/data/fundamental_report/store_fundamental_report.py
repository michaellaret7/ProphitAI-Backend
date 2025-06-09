import psycopg2
import datetime

from dotenv import load_dotenv
from backend.src.utils.file_utils import load_schema_data
from backend.src.utils.database import get_default_db_config, get_cursor
from backend.src.data.fundamental_report.generate_fundamental_report import generate_fundamental_analysis_report

# Load environment variables from .env file
load_dotenv()

def create_report_table_if_not_exists(cursor, schema_name: str, table_name: str):
    """
    Create fundamental analysis report table if it doesn't exist.
    
    Creates a table with sanitized schema and table names to store fundamental
    analysis reports with ID, content, and timestamp columns.
    
    Args:
        cursor: Database cursor object for executing queries.
        schema_name: The schema name to create the table in.
        table_name: The name of the table to create.
        
    Returns:
        None
        
    Raises:
        psycopg2.Error: If table creation fails.
    """
    # Sanitize schema name (basic but important for security and compatibility)
    safe_schema_name = schema_name.lower().replace('-', '_').replace('.', '_')
    if not safe_schema_name or not safe_schema_name[0].isalpha():
        safe_schema_name = f"_{safe_schema_name}"

    # Sanitize table name
    safe_table_name = table_name.lower().replace('-', '_').replace('.', '_')
    if not safe_table_name or not safe_table_name[0].isalpha():
        safe_table_name = f"_{safe_table_name}"

    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS "{safe_schema_name}"."{safe_table_name}" (
        id SERIAL PRIMARY KEY,
        report_text TEXT,
        generation_timestamp TIMESTAMP WITH TIME ZONE
    );
    """
    try:
        cursor.execute(create_table_sql)
        # print(f"Table '{safe_schema_name}.{safe_table_name}' ensured to exist.") # Optional: for debugging
    except psycopg2.Error as e:
        print(f"Error creating table {safe_schema_name}.{safe_table_name}: {e}")
        cursor.connection.rollback() # Rollback if table creation fails
        raise # Re-raise the exception to be handled by the caller

def get_tickers_and_schemas_for_sector(sector_db_name: str, schema_data: dict) -> dict[str, str]:
    """
    Extract ticker-to-schema mapping for a specific sector database.
    
    Parses the database schema definition to create a mapping of ticker symbols
    to their corresponding schema names within the given sector database.
    
    Args:
        sector_db_name: The name of the target sector database (e.g., 'equity_sector_energy_fundamentals').
        schema_data: The loaded database schema structure from database_schemas.json.
        
    Returns:
        Dict[str, str]: Dictionary mapping uppercase ticker symbols to their schema names.
    """
    ticker_schema_map = {}
    # Match the base DB name (e.g., equity_sector_energy) found in the schema keys
    target_base_db_name = sector_db_name.replace('_fundamentals', '')

    # The top level key in schema_data IS the base db name we need
    sector_info = schema_data.get(target_base_db_name)

    if sector_info:
        # sector_info holds the data for the matched sector, including "schemas"
        for schema_name, schema_info in sector_info.get("schemas", {}).items():
            # schema_info holds {"tables": ...}
            for table_category, table_data in schema_info.get("tables", {}).items():
                 # table_data is the dictionary like {"tickers": [...]}
                for ticker in table_data.get("tickers", []):
                    ticker_schema_map[ticker.upper()] = schema_name # Map ticker to its schema
    else:
        print(f"Warning: Database key '{target_base_db_name}' not found directly in schema_data.")
        # Fallback to iterating if the key structure is different than expected
        for db_key, potential_sector_info in schema_data.items():
             # Check if the nested database matches
            if potential_sector_info.get("database") == target_base_db_name:
                for schema_name, schema_info in potential_sector_info.get("schemas", {}).items():
                    for table_category, table_data in schema_info.get("tables", {}).items():
                        for ticker in table_data.get("tickers", []):
                           ticker_schema_map[ticker.upper()] = schema_name # Map ticker to its schema
                break # Found the matching sector database via iteration

    if not ticker_schema_map:
        print(f"Warning: No tickers found for database '{sector_db_name}' using key '{target_base_db_name}' in schema definition.")

    # Return the dictionary directly, sorting is not needed for keys
    return ticker_schema_map

def store_report(cursor, schema_name: str, table_name: str, report_content: str):
    """
    Store fundamental analysis report in the specified database table.
    
    Truncates the existing table and inserts the new report with current timestamp.
    
    Args:
        cursor: Database cursor object for executing queries.
        schema_name: The schema name containing the target table.
        table_name: The name of the table to store the report in.
        report_content: The generated fundamental analysis report text.
        
    Returns:
        None
        
    Raises:
        psycopg2.Error: If report storage fails.
    """
    # Sanitize schema name (basic)
    safe_schema_name = schema_name.lower().replace('-', '_').replace('.', '_')
    if not safe_schema_name or not safe_schema_name[0].isalpha():
        safe_schema_name = f"_{safe_schema_name}"

    # Sanitize table name (repeat sanitization for safety)
    safe_table_name = table_name.lower().replace('-', '_').replace('.', '_')
    if not safe_table_name or not safe_table_name[0].isalpha():
         safe_table_name = f"_{safe_table_name}"

    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        # Clear previous report if table exists and has data
        cursor.execute(f'TRUNCATE TABLE "{safe_schema_name}"."{safe_table_name}";')

        # Insert the new report
        insert_sql = f"""
        INSERT INTO "{safe_schema_name}"."{safe_table_name}" (report_text, generation_timestamp)
        VALUES (%s, %s);
        """
        cursor.execute(insert_sql, (report_content, now))
        # print(f"Stored report in '{safe_schema_name}.{safe_table_name}'.") # Too verbose
    except psycopg2.Error as e:
        print(f"Error storing report in {safe_schema_name}.{safe_table_name}: {e}")
        cursor.connection.rollback() # Rollback the specific failed transaction
        raise # Re-raise

def main(sector_db_name: str, target_schema_name: str | None = None):
    """
    Generate and store fundamental reports for all tickers in a sector database.
    
    Orchestrates the complete workflow of loading schema data, finding tickers,
    generating fundamental analysis reports, and storing them in the database.
    
    Args:
        sector_db_name: The name of the sector database to process.
        target_schema_name: Optional specific schema to target within the sector.
        
    Returns:
        None - Prints processing summary to console.
    """
    print(f"Starting fundamental report generation for database: {sector_db_name}")
    if target_schema_name:
        print(f"Targeting specific schema: {target_schema_name}")

    schema_data = load_schema_data()
    if not schema_data:
        print("Error: Could not load database schema data. Exiting.")
        return

    ticker_schema_map = get_tickers_and_schemas_for_sector(sector_db_name, schema_data)
    if not ticker_schema_map:
        print(f"No tickers found for {sector_db_name}. Exiting.")
        return

    # Filter by target schema if provided
    if target_schema_name:
        # Sanitize the target schema name for comparison (lowercase, replace -, .)
        safe_target_schema = target_schema_name.lower().replace('-', '_').replace('.', '_')
        if not safe_target_schema or not safe_target_schema[0].isalpha():
             safe_target_schema = f"_{safe_target_schema}"

        filtered_ticker_schema_map = {
            ticker: schema
            for ticker, schema in ticker_schema_map.items()
            # Sanitize original schema from map for comparison
            if schema.lower().replace('-', '_').replace('.', '_') == safe_target_schema or f"_{schema.lower().replace('-', '_').replace('.', '_')}" == safe_target_schema
        }
        if not filtered_ticker_schema_map:
            print(f"No tickers found for schema '{target_schema_name}' within database '{sector_db_name}'. Exiting.")
            return
        ticker_schema_map = filtered_ticker_schema_map # Use the filtered map
        print(f"Found {len(ticker_schema_map)} tickers for schema: {target_schema_name}")
    else:
        # Removed slicing logic to process all tickers
        print(f"Found {len(ticker_schema_map)} total tickers for {sector_db_name}. Processing all.")

    db_config = get_default_db_config()
    processed_count = 0
    skipped_count = 0
    error_count = 0

    try:
        with get_cursor(dbname=sector_db_name, db_config=db_config) as cur:

            for ticker, original_schema in ticker_schema_map.items(): # <-- Iterate over all items
                # Sanitize the original schema name before using it
                safe_original_schema = original_schema.lower().replace('-', '_').replace('.', '_')
                print(f"Processing ticker: {ticker} (Schema: {safe_original_schema})...")
                try:
                    # Ensure the original schema exists in the _fundamentals DB first
                    # create_schema_if_not_exists(cur, safe_original_schema) # Removed call
                    # Commit schema creation separately? Or wait until report stored?
                    # Let's commit after storing report for atomicity per ticker.

                    # Generate the report
                    report = generate_fundamental_analysis_report(ticker)

                    # Check if report generation was successful
                    if report and not report.startswith("No fundamental data found") and not report.startswith("Error analyzing"):
                        table_name = f"{ticker}_fundamental_report" # Use ticker directly for table name
                        # Use the original_schema here
                        create_report_table_if_not_exists(cur, safe_original_schema, table_name) # Removed call
                        store_report(cur, safe_original_schema, table_name, report)
                        cur.connection.commit() # Commit after each successful ticker processing
                        print(f"  Successfully generated and stored report for {ticker} in schema {safe_original_schema}.")
                        processed_count += 1
                    else:
                        print(f"  Skipping {ticker}: {report[:150]}...") # Show beginning of error/skip message
                        skipped_count += 1

                except psycopg2.Error as db_err:
                    print(f"  Database error processing {ticker} in schema {safe_original_schema}: {db_err}")
                    cur.connection.rollback() # Ensure rollback on DB error for the ticker
                    error_count += 1
                except Exception as gen_err:
                    print(f"  Report generation error for {ticker}: {gen_err}")
                    # No need to rollback if the error was before DB operations for this ticker
                    error_count += 1

    except psycopg2.OperationalError as conn_err:
        print(f"\nDatabase connection error for {sector_db_name}: {conn_err}")
        print("Please check database credentials and reachability.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\n----- Processing Summary -----") # Removed (Test Run)
        print(f"Total tickers found in sector: {len(ticker_schema_map)}")
        # Removed "Tickers attempted" line as it's now the same as total found
        print(f"Successfully processed: {processed_count}")
        print(f"Skipped (no data/error in generation): {skipped_count}")
        print(f"Errors (DB or other exceptions): {error_count}")
        print("-----------------------------") # Adjusted dashes

if __name__ == "__main__":
    # Example: Rerun only the 'communications_equipment' schema for the IT sector
    # sector_db_name = "equity_sector_information_technology_fundamentals"
    # target_schema = "communications_equipment"
    # print(f"Running specifically for: Database='{sector_db_name}', Schema='{target_schema}'")
    # main(sector_db_name=sector_db_name, target_schema_name=target_schema)


    # --- Previous execution logic (commented out) ---
    # sector_db_name = "equity_sector_communication_services_fundamentals" # Done
    # sector_db_name = "equity_sector_consumer_discretionary_fundamentals" # Done
    # sector_db_name = "equity_sector_consumer_staples_fundamentals" # Done
    # sector_db_name2 = "equity_sector_energy_fundamentals" # Done
    # sector_db_name3 = "equity_sector_financials_fundamentals" # Done
    # sector_db_name1 = "equity_sector_health_care_fundamentals" # <<< Set to Healthcare
    # sector_db_name2 = "equity_sector_industrials_fundamentals" # <<< Set to Industrials
    # sector_db_name3 = "equity_sector_information_technology_fundamentals" # <<< Set to Information Technology
    sector_db_name4 = "equity_sector_materials_fundamentals" # <<< Set to Materials
    sector_db_name5 = "equity_sector_real_estate_fundamentals" # <<< Set to Real Estate
    sector_db_name6 = "equity_sector_utilities_fundamentals" # <<< Set to Utilities
    # # -------------------------------------------- #

    main(sector_db_name4)
    main(sector_db_name5)
    main(sector_db_name6)

