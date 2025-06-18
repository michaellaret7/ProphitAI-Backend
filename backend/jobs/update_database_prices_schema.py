import os
import json
import psycopg2
import re
from backend.src.utils.database import get_pooled_connection, get_default_db_config

def create_prices_schema_file(output_file="database_schemas_prices.json"):
    """
    Extract price database schemas and save to JSON file.
    
    Connects to databases ending with '_prices', extracts their schema and table
    information, and writes the hierarchical structure to a JSON file.
    
    Args:
        output_file: The filename for the output JSON file (default: "database_schemas_prices.json")
        
    Returns:
        Dict: The extracted price schemas data structure.
    """
    # Database connection parameters from environment
    db_config = get_default_db_config()

    # Initialize the structure for price schemas
    prices_schemas_data = {}

    try:
        # Connect to the main 'postgres' database to list all databases
        conn, cursor = get_pooled_connection("postgres", db_config, autocommit=True)
        if not conn or not cursor:
            raise Exception("Failed to connect to postgres database")

        # Query to get all database names
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        all_databases = [row[0] for row in cursor.fetchall()]

        # Filter for databases ending with '_prices'
        prices_databases = [db for db in all_databases if db.endswith('_prices')]
        print(f"Found {len(prices_databases)} databases ending with '_prices'.")

        cursor.close()

        # Process each prices database
        for db_name in prices_databases:
            print(f"Processing database: {db_name}")
            prices_schemas_data[db_name] = {} # Initialize as dict for schemas->tables mapping
            try:
                # Connect to the specific prices database
                db_conn, db_cursor = get_pooled_connection(db_name, db_config, autocommit=True)
                if not db_conn or not db_cursor:
                    print(f"  Failed to connect to {db_name}")
                    continue

                # Query for schemas within this database that end with '_prices'
                db_cursor.execute("""
                    SELECT schema_name FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
                    AND schema_name LIKE '%_prices'
                """)

                schemas_in_db = [row[0] for row in db_cursor.fetchall()]

                if schemas_in_db:
                    # Process each found schema
                    for schema_name in schemas_in_db:
                        print(f"  Processing schema: {schema_name}")
                        # Query for tables within this schema
                        db_cursor.execute(f"""
                            SELECT table_name FROM information_schema.tables
                            WHERE table_schema = '{schema_name}'
                        """)
                        table_names = sorted([row[0] for row in db_cursor.fetchall()])
                        prices_schemas_data[db_name][schema_name] = table_names
                        print(f"    Found tables: {', '.join(table_names) if table_names else 'None'}")
                else:
                    # No matching schemas found in this DB, already handled by initializing prices_schemas_data[db_name] = {}
                    print(f"  No schemas ending with '_prices' found in {db_name}.")

                db_cursor.close()
            except Exception as e:
                print(f"  Error processing database {db_name}: {e}")

    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")

    # --- MODIFIED ---
    # Construct a path to backend/src/data/database regardless of where the script is run from.
    # This assumes the script is run from the project root.
    output_dir = os.path.join("backend", "src", "data", "database")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir) # Ensure the directory exists
    output_path = os.path.join(output_dir, output_file)
    # --- END MODIFIED ---
    
    try:
        with open(output_path, 'w') as f:
            json.dump(prices_schemas_data, f, indent=4)
        print(f"Successfully created prices schema file: {output_path}")
    except IOError as e:
        print(f"Error writing to file {output_path}: {e}")

    return prices_schemas_data

if __name__ == "__main__":
    create_prices_schema_file() 