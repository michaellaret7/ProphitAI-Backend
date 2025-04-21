import os
import json
import psycopg2
import re

def create_connection(db_config, dbname):
    """Create a new database connection with autocommit mode enabled"""
    conn_config = db_config.copy()
    conn_config['dbname'] = dbname
    conn = psycopg2.connect(**conn_config)
    conn.autocommit = True  # Prevent transaction issues
    return conn

def create_prices_schema_file(output_file="database_schemas_prices.json"):
    """
    Connects to the database and extracts information about databases and schemas
    ending with '_prices', writing the result to a JSON file.

    Args:
        output_file (str): The file to write the extracted price schema information to.
    """
    # Database connection parameters (same as the other script)
    db_config = {
        "host": "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com",
        "user": "postgres",
        "password": "ml1710402!",
        "port": "5432"
    }

    # Initialize the structure for price schemas
    prices_schemas_data = {}
    conn = None

    try:
        # Connect to the main 'postgres' database to list all databases
        conn = create_connection(db_config, "postgres")
        cursor = conn.cursor()

        # Query to get all database names
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        all_databases = [row[0] for row in cursor.fetchall()]

        # Filter for databases ending with '_prices'
        prices_databases = [db for db in all_databases if db.endswith('_prices')]
        print(f"Found {len(prices_databases)} databases ending with '_prices'.")

        cursor.close()
        conn.close() # Close the connection to 'postgres'

        # Process each prices database
        for db_name in prices_databases:
            print(f"Processing database: {db_name}")
            db_conn = None
            prices_schemas_data[db_name] = {} # Initialize as dict for schemas->tables mapping
            try:
                # Connect to the specific prices database
                db_conn = create_connection(db_config, db_name)
                db_cursor = db_conn.cursor()

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
                db_conn.close()
            except Exception as e:
                print(f"  Error processing database {db_name}: {e}")
                if db_conn:
                    db_conn.close()

    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
    finally:
        if conn:
            conn.close()

    # Write the prices schemas data to the specified output file
    output_path = os.path.join('src', 'data', output_file)
    try:
        with open(output_path, 'w') as f:
            json.dump(prices_schemas_data, f, indent=4)
        print(f"Successfully created prices schema file: {output_path}")
    except IOError as e:
        print(f"Error writing to file {output_path}: {e}")

    return prices_schemas_data

if __name__ == "__main__":
    create_prices_schema_file() 