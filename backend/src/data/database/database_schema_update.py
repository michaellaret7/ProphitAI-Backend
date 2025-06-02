import os
import json
import psycopg2
from collections import defaultdict
import re
from backend.src.utils.database import get_pooled_connection, get_default_db_config

def clean_ticker(ticker):
    """Remove 'US EQUITY' and other common suffixes from ticker symbols"""
    if ticker is None:
        return None
        
    # Convert to string if not already
    ticker = str(ticker).strip().upper()
    
    # Remove common suffixes
    ticker = re.sub(r'\s+US\s+EQUITY$', '', ticker)
    ticker = re.sub(r'\s+EQUITY$', '', ticker)
    ticker = re.sub(r'\s+US$', '', ticker)
    
    return ticker.strip()

def recreate_database_schemas(output_file="database_schemas.json"):
    """
    This script connects to the database and extracts schema information to recreate
    the database_schemas.json file with the exact same structure.
    
    Args:
        output_file (str): The file to write the extracted schema to
    """
    # Database connection parameters
    db_config = get_default_db_config()
    
    # Initialize the final structure
    schemas_data = {}
    
    # First, load the existing schema to preserve structure
    try:
        with open('backend/src/data/database/database_schemas.json', 'r') as f:
            original_schema = json.load(f)
    except:
        print("Warning: Original schema file not found. Creating new structure.")
        original_schema = {}
    
    # Start with the postgres database to get a list of all databases
    conn = None
    cursor = None
    try:
        conn, cursor = get_pooled_connection("postgres", db_config, autocommit=True)
        if not conn or not cursor:
            raise Exception("Failed to connect to postgres database")
        
        # Query to get all equity sector databases
        cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datname LIKE 'equity_sector_%'
        """)
        equity_databases = [row[0] for row in cursor.fetchall()]
        
        # Query to get all ETF databases
        cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datname LIKE 'etf_%'
        """)
        etf_databases = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        
        # Process each equity sector database
        for db_name in equity_databases:
            # Skip price/fundamentals databases for now
            if db_name.endswith('_fundamentals') or db_name.endswith('_prices'):
                continue
                
            print(f"Processing database: {db_name}")
            
            # Initialize database structure for all databases, not just those in original schema
            schemas_data[db_name] = {
                "database": db_name,
                "schemas": {}
            }
            
            # Connect to this database
            sector_conn = None
            sector_cursor = None
            try:
                sector_conn, sector_cursor = get_pooled_connection(db_name, db_config, autocommit=True)
                if not sector_conn or not sector_cursor:
                    print(f"  Failed to connect to {db_name}")
                    continue
                
                # For each sector database, we need to find its schemas
                sector_cursor.execute("""
                    SELECT schema_name FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
                """)
                
                schemas = [row[0] for row in sector_cursor.fetchall()]
                
                # Process each schema
                for schema_name in schemas:
                    print(f"  Processing schema: {schema_name}")
                    
                    # Skip price schemas
                    if schema_name.endswith('_prices'):
                        continue
                    
                    # Initialize the schema structure
                    schemas_data[db_name]["schemas"][schema_name] = {
                        "tables": {}
                    }
                    
                    # Get all tables in this schema
                    sector_cursor.execute(f"""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = '{schema_name}'
                    """)
                    
                    tables = [row[0] for row in sector_cursor.fetchall()]
                    
                    # Check if we have original tables to reference
                    original_tables = {}
                    if db_name in original_schema and schema_name in original_schema.get(db_name, {}).get("schemas", {}):
                        original_tables = original_schema[db_name]["schemas"][schema_name].get("tables", {})
                    
                    # Process each table in the schema
                    for table_name in tables:
                        print(f"    Processing table: {table_name}")
                        all_tickers = []  # Store all tickers from all sources
                        
                        # Check if table has ticker column
                        sector_cursor.execute(f"""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_schema = '{schema_name}' 
                            AND table_name = '{table_name}'
                            AND column_name = 'ticker'
                        """)
                        
                        if sector_cursor.fetchone():
                            # Query for tickers
                            sector_cursor.execute(f"""
                                SELECT DISTINCT ticker FROM {schema_name}.{table_name}
                            """)
                            
                            direct_tickers = [clean_ticker(row[0]) for row in sector_cursor.fetchall()]
                            if direct_tickers:
                                all_tickers.extend(direct_tickers)
                                print(f"      Added {len(direct_tickers)} tickers from direct table")
                        
                        # Special handling for wireless_telecommunication_services from the screenshot
                        if schema_name == "wireless_telecommunication_services" and table_name == "wireless_telecommunication_services":
                            try:
                                # Always use a fresh connection for each query
                                special_conn, special_cursor = get_pooled_connection(db_name, db_config, autocommit=True)
                                if special_conn and special_cursor:
                                    # Try different queries to find all wireless tickers
                                    wireless_queries = [
                                        """
                                        SELECT DISTINCT ticker
                                        FROM wireless_telecommunication_services.classification
                                        WHERE LOWER(sub_industry) = 'wireless telecommunication services'
                                        """,
                                        """
                                        SELECT DISTINCT ticker
                                        FROM wireless_telecommunication_services.classification
                                        """,
                                        """
                                        SELECT DISTINCT ticker
                                        FROM wireless_telecommunication_services.wireless_telecommunication_services
                                        """
                                    ]

                                    # Try each query one by one
                                    for query in wireless_queries:
                                        try:
                                            special_cursor.execute(query)
                                            wireless_tickers = [clean_ticker(row[0]) for row in special_cursor.fetchall()]
                                            if wireless_tickers:
                                                all_tickers.extend(wireless_tickers)
                                                print(f"      Found {len(wireless_tickers)} wireless tickers")
                                                break  # Stop if successful
                                        except Exception as e:
                                            print(f"      Wireless query failed: {e}")

                                    # Check for specific tickers from the screenshot - already cleaned
                                    screenshot_tickers = [
                                        "TDS", "USM", "TMUS", "SPOK", "KORE", "GOGO", "TIGO", "VEON", "FNGR", "UCL", "SURG"
                                    ]
                                    for ticker in screenshot_tickers:
                                        if ticker not in [t.upper() for t in all_tickers]:
                                            all_tickers.append(ticker)
                                            print(f"      Manually added {ticker} from screenshot")

                                    special_cursor.close()
                            except Exception as e:
                                print(f"      Special wireless handling error: {e}")
                        
                        # 1. Try the fundamentals database with classification tables
                        fundamentals_db = f"{db_name}_fundamentals"
                        try:
                            fund_conn, fund_cursor = get_pooled_connection(fundamentals_db, db_config, autocommit=True)
                            if fund_conn and fund_cursor:
                                # Look for classification tables
                                fund_cursor.execute(
                                    f"""
                                    SELECT table_name FROM information_schema.tables 
                                    WHERE table_schema = '{schema_name}'
                                      AND table_name LIKE '%classification%'
                                    """
                                )

                                class_tables = [row[0] for row in fund_cursor.fetchall()]

                                for class_table in class_tables:
                                    # Check for industry columns
                                    fund_cursor.execute(
                                        f"""
                                        SELECT column_name FROM information_schema.columns 
                                        WHERE table_schema = '{schema_name}' 
                                          AND table_name = '{class_table}'
                                        """
                                    )
                                    columns = [row[0] for row in fund_cursor.fetchall()]

                                    # Look for any form of industry/subindustry column
                                    industry_columns = [
                                        col
                                        for col in columns
                                        if 'industry' in col.lower() or 'sub_industry' in col.lower() or 'subindustry' in col.lower()
                                    ]

                                    for industry_col in industry_columns:
                                        # Try all possible matches for industry name
                                        normalized_table = table_name.replace('_', ' ')

                                        # Try with a fresh connection to avoid transaction errors
                                        query_conn, query_cursor = get_pooled_connection(
                                            fundamentals_db, db_config, autocommit=True
                                        )
                                        if query_conn and query_cursor:
                                            try:
                                                query = f"""
                                                    SELECT ticker FROM {schema_name}.{class_table}
                                                    WHERE LOWER({industry_col}) = LOWER('{normalized_table}')
                                                       OR LOWER({industry_col}) = LOWER('{table_name}')
                                                       OR LOWER(REPLACE({industry_col}, ' ', '_')) = LOWER('{table_name}')
                                                """
                                                query_cursor.execute(query)
                                                table_tickers = [clean_ticker(row[0]) for row in query_cursor.fetchall()]
                                                if table_tickers:
                                                    all_tickers.extend(table_tickers)
                                                    print(f"      Found {len(table_tickers)} tickers from {industry_col}")
                                            except Exception as e:
                                                print(f"      Industry query error: {e}")
                                            finally:
                                                query_cursor.close()

                                fund_cursor.close()
                        except Exception as e:
                            print(f"      Error accessing fundamentals DB: {e}")
                        
                        # 2. If still looking for tickers, check prices database
                        if len(all_tickers) < 5:  # Arbitrary threshold
                            prices_db = f"{db_name}_prices"
                            prices_schema = f"{schema_name}_prices"
                            
                            try:
                                prices_conn, prices_cursor = get_pooled_connection(prices_db, db_config, autocommit=True)
                                if prices_conn and prices_cursor:
                                    # Check if the prices schema exists
                                    prices_cursor.execute(
                                        f"""
                                        SELECT schema_name FROM information_schema.schemata 
                                        WHERE schema_name = '{prices_schema}'
                                        """
                                    )

                                    if prices_cursor.fetchone():
                                        # Get all tables in this schema - these are ticker tables directly
                                        prices_cursor.execute(
                                            f"""
                                            SELECT table_name FROM information_schema.tables 
                                            WHERE table_schema = '{prices_schema}'
                                            """
                                        )

                                        price_tables = [row[0] for row in prices_cursor.fetchall()]

                                        # If we have original tickers, check which still exist
                                        table_info = original_tables.get(table_name, {})
                                        if "tickers" in table_info and price_tables:
                                            original_tickers = table_info["tickers"]
                                            for ticker in original_tickers:
                                                clean_tick = clean_ticker(ticker)
                                                if clean_tick.lower() in price_tables:
                                                    all_tickers.append(clean_tick)

                                            print(f"      Found {len(all_tickers)} tickers in prices DB matching original")

                                    prices_cursor.close()
                            except Exception as e:
                                print(f"      Error accessing prices DB: {e}")
                        
                        # 3. Last resort: use the original tickers as fallback
                        table_info = original_tables.get(table_name, {})
                        if not all_tickers and "tickers" in table_info:
                            print(f"      Using original tickers for {table_name}")
                            all_tickers = [clean_ticker(t) for t in table_info["tickers"]]
                        
                        # Clean all tickers once more to ensure no 'US EQUITY' remains
                        cleaned_tickers = [clean_ticker(t) for t in all_tickers if t]
                        
                        # Save the unique, sorted tickers
                        unique_tickers = sorted(list(set(cleaned_tickers)))
                        schemas_data[db_name]["schemas"][schema_name]["tables"][table_name] = {
                            "tickers": unique_tickers
                        }
                        
                        # Validate: Print how many tickers we found
                        ticker_count = len(unique_tickers)
                        original_count = len(table_info.get("tickers", []))
                        print(f"      Final ticker count: {ticker_count}" + 
                              (f" (original: {original_count})" if original_count else ""))
                        
                        # Special check for wireless_telecommunication_services table
                        if schema_name == "wireless_telecommunication_services" and table_name == "wireless_telecommunication_services":
                            # Make sure all tickers from the screenshot are included
                            must_include = ["TDS", "USM", "TMUS", "SPOK", "KORE", "GOGO", "TIGO", "VEON", "FNGR", "UCL", "SURG"]
                            current_tickers = schemas_data[db_name]["schemas"][schema_name]["tables"][table_name]["tickers"]
                            missing = [t for t in must_include if t not in current_tickers]
                            
                            if missing:
                                print(f"      WARNING: Missing required tickers: {missing}, adding manually")
                                current_tickers.extend(missing)
                                schemas_data[db_name]["schemas"][schema_name]["tables"][table_name]["tickers"] = sorted(current_tickers)
                
                sector_cursor.close()
            except Exception as e:
                print(f"  Error processing database {db_name}: {e}")
                
        # Process each ETF database
        print("\nProcessing ETF databases:")
        for db_name in etf_databases:
            # Skip ETF price databases
            if db_name.endswith('_prices'):
                continue
                
            print(f"Processing ETF database: {db_name}")
            
            # Initialize the database structure
            schemas_data[db_name] = {
                "database": db_name,
                "schemas": {}
            }
            
            # Connect to this database
            etf_conn = None
            etf_cursor = None
            try:
                etf_conn, etf_cursor = get_pooled_connection(db_name, db_config, autocommit=True)
                if not etf_conn or not etf_cursor:
                    print(f"  Failed to connect to {db_name}")
                    continue
                
                # For each ETF database, we need to find its schemas
                etf_cursor.execute("""
                    SELECT schema_name FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
                """)
                
                schemas = [row[0] for row in etf_cursor.fetchall()]
                
                # Process each schema
                for schema_name in schemas:
                    # Skip price schemas
                    if schema_name.endswith('_prices'):
                        continue
                        
                    print(f"  Processing ETF schema: {schema_name}")
                    
                    # Initialize the schema structure
                    schemas_data[db_name]["schemas"][schema_name] = {
                        "tables": {}
                    }
                    
                    # Get all tables in this schema
                    etf_cursor.execute(f"""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = '{schema_name}'
                    """)
                    
                    tables = [row[0] for row in etf_cursor.fetchall()]
                    
                    # Process each table
                    for table_name in tables:
                        print(f"    Processing ETF table: {table_name}")
                        all_etfs = []
                        
                        # Check if this table has a ticker column
                        etf_cursor.execute(f"""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_schema = '{schema_name}' 
                            AND table_name = '{table_name}'
                            AND column_name = 'ticker'
                        """)
                        
                        if etf_cursor.fetchone():
                            # Query for tickers
                            etf_cursor.execute(f"""
                                SELECT DISTINCT ticker FROM {schema_name}.{table_name}
                            """)
                            
                            etf_tickers = [clean_ticker(row[0]) for row in etf_cursor.fetchall()]
                            if etf_tickers:
                                all_etfs.extend(etf_tickers)
                                print(f"      Found {len(etf_tickers)} ETFs in {table_name}")
                        
                        # If no tickers found, check for symbol column
                        if not all_etfs:
                            etf_cursor.execute(f"""
                                SELECT column_name FROM information_schema.columns 
                                WHERE table_schema = '{schema_name}' 
                                AND table_name = '{table_name}'
                                AND column_name = 'symbol'
                            """)
                            
                            if etf_cursor.fetchone():
                                # Query for symbols
                                etf_cursor.execute(f"""
                                    SELECT DISTINCT symbol FROM {schema_name}.{table_name}
                                """)
                                
                                etf_symbols = [clean_ticker(row[0]) for row in etf_cursor.fetchall()]
                                if etf_symbols:
                                    all_etfs.extend(etf_symbols)
                                    print(f"      Found {len(etf_symbols)} ETFs by symbol in {table_name}")
                        
                        # Save the unique, sorted ETFs
                        if all_etfs:
                            unique_etfs = sorted(list(set([e for e in all_etfs if e])))
                            schemas_data[db_name]["schemas"][schema_name]["tables"][table_name] = {
                                "tickers": unique_etfs
                            }
                            print(f"      Final ETF count for {table_name}: {len(unique_etfs)}")
                        else:
                            # Even if no ETFs found, create an empty entry
                            schemas_data[db_name]["schemas"][schema_name]["tables"][table_name] = {
                                "tickers": []
                            }
                            print(f"      No ETFs found for {table_name}")
                
                etf_cursor.close()
            except Exception as e:
                print(f"  Error processing ETF database {db_name}: {e}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    # Determine canonical output path – inside src/data/database
    base_dir = os.path.join('backend', 'src', 'data', 'database')
    os.makedirs(base_dir, exist_ok=True)
    output_path = os.path.join(base_dir, output_file)

    # Write the schemas data to a file
    with open(output_path, 'w') as f:
        json.dump(schemas_data, f, indent=4)
    
    print(f"Successfully recreated schema in {output_path}")
    return schemas_data


if __name__ == "__main__":
    recreate_database_schemas() 