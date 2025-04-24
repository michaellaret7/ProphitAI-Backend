import psycopg2
from ib_insync import *
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy import create_engine, text, inspect, MetaData
import time
from psycopg2.extras import execute_values
import os

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the full path to the Excel file
excel_file_path = os.path.join(script_dir, 'FinalSectorSheet.xlsx')

class IBKRDatabase:
    def __init__(self, host="demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com", 
                 user="postgres", password="ml1710402!", port="5432"):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.ib = IB()
        self.conn_pool = {}  # Add a connection pool dictionary

    # connect to the cloud database AWS
    def connect_to_cloud_database(self, db_name):
        # Check if we have a connection in our pool that we can reuse
        if db_name in self.conn_pool and self.conn_pool[db_name] is not None:
            try:
                # Test if the connection is still good with a simple query
                cursor = self.conn_pool[db_name].cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                print(f"✅ Reusing existing connection to {db_name}")
                return self.conn_pool[db_name], self.conn_pool[db_name].cursor()
            except psycopg2.Error:
                # If connection is broken, close it and create a new one
                try:
                    self.conn_pool[db_name].close()
                except:
                    pass
                self.conn_pool[db_name] = None
                
        # Create a new connection if needed
        try:
            conn = psycopg2.connect(
                host=self.host,
                database=db_name,
                user=self.user,
                password=self.password,
                port=self.port
            )
            print(f"✅ Successfully connected to {db_name} database")
            conn.autocommit = True
            cursor = conn.cursor()
            # Store in connection pool for reuse
            self.conn_pool[db_name] = conn
            return conn, cursor

        except psycopg2.Error as e:
            print(f"⚠️ Error connecting to database: {e}")
            return None, None

    # connect to the local database
    def connect_to_local_database(self, db_name):
        # Check if we have a local connection in our pool that we can reuse
        local_key = f"local_{db_name}"
        if local_key in self.conn_pool and self.conn_pool[local_key] is not None:
            try:
                # Test if the connection is still good with a simple query
                cursor = self.conn_pool[local_key].cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                print(f"✅ Reusing existing local connection to {db_name}")
                return self.conn_pool[local_key], self.conn_pool[local_key].cursor()
            except psycopg2.Error:
                # If connection is broken, close it and create a new one
                try:
                    self.conn_pool[local_key].close()
                except:
                    pass
                self.conn_pool[local_key] = None
                
        # Create a new connection if needed
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="postgres",
                user="postgres",
                password="Ml1710402!"
            )
            print(f"✅ Successfully connected to local {db_name} database")
            conn.autocommit = True
            cursor = conn.cursor()
            # Store in connection pool for reuse
            self.conn_pool[local_key] = conn
            return conn, cursor

        except psycopg2.Error as e:
            print(f"⚠️ Error connecting to local database: {e}")
            return None, None

    def close_connection(self, db_name=None):
        """Explicitly close database connections"""
        if db_name:
            # Handle both cloud and local connections
            for prefix in ["", "local_"]:
                key = f"{prefix}{db_name}"
                if key in self.conn_pool and self.conn_pool[key]:
                    try:
                        self.conn_pool[key].close()
                        self.conn_pool[key] = None
                        print(f"✅ Closed connection to {key}")
                    except Exception as e:
                        print(f"⚠️ Error closing connection to {key}: {e}")
        else:
            # Close all connections
            for db, conn in list(self.conn_pool.items()):
                if conn:
                    try:
                        conn.close()
                        self.conn_pool[db] = None
                        print(f"✅ Closed connection to {db}")
                    except Exception as e:
                        print(f"⚠️ Error closing connection to {db}: {e}")
                        
    def __del__(self):
        """Destructor to ensure connections are closed when the object is garbage collected"""
        self.close_connection()

    # create a database by name if it doesn't exist
    def create_database(self, db_name):
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                database="postgres",  
                user=self.user,
                password=self.password,
                port=self.port
            )
            conn.autocommit = True
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cursor.fetchone()
            
            if not exists:
                try:
                    cursor.execute(f"CREATE DATABASE {db_name}")
                    print(f"✅Database '{db_name}' created successfully")
                except psycopg2.Error as e:
                    print(f"⚠️ Error creating database: {e}")
            else:
                print(f"📄 Database '{db_name}' already exists")

            return db_name
        except Exception as e:
            print(f"⚠️ Error in create_database: {e}")
            return db_name
        finally:
            # Ensure connections are properly closed
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # delete a database by name if it exists
    def delete_database(self, db_name):
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                database="postgres",  # Connect to default postgres database
                user=self.user,
                password=self.password,
                port=self.port
            )
            conn.autocommit = True
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cursor.fetchone()
            
            if exists:
                # Terminate all connections to the database before dropping
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{db_name}'
                    AND pid <> pg_backend_pid();
                """)
                
                # Drop the database
                cursor.execute(f"DROP DATABASE {db_name}")
                print(f"✅ Database '{db_name}' deleted successfully")
                
                # Remove from connection pool if it exists
                if db_name in self.conn_pool:
                    del self.conn_pool[db_name]
            else:
                print(f"📄 Database '{db_name}' does not exist")

        except psycopg2.Error as e:
            print(f"⚠️ Error deleting database: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # fetch data from IBKR: Takes a contract, duration, and bar size setting
    def fetch_ibkr_data(self, contract, durationStr, barSizeSetting):
        try:
            if self.ib.isConnected():
                self.ib.disconnect()
                
            self.ib.connect('127.0.0.1', 4002, clientId=1)
            qualified_contract = self.ib.qualifyContracts(contract)[0]
            print(f"Fetching data for contract: {qualified_contract}")
            
            bars = self.ib.reqHistoricalData(
                qualified_contract,
                endDateTime='',
                durationStr=durationStr,
                barSizeSetting=barSizeSetting,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )

            if bars:
                df = util.df(bars)
                df['timestamp'] = pd.to_datetime(df['date'])
                # First round the existing numeric columns
                numeric_columns = ['open', 'high', 'low', 'close', 'average']
                df[numeric_columns] = df[numeric_columns].round(3)
                # Then create and round bar_delta (renamed from barDelta)
                df['bar_delta'] = (df['close'] - df['open']).round(3)
                df['day_of_week'] = df['timestamp'].dt.day_name()
                # Rename barCount to bar_count
                if 'barCount' in df.columns:
                    df = df.rename(columns={'barCount': 'bar_count'})
                df = df.drop(columns=['timestamp'])
                print(f"Retrieved {len(df)} bars of data")
                print(df)
                return df
            print(f"No data returned for {contract.symbol}")
            return None
        except Exception as e:
            print(f"Error fetching data for {contract.symbol}: {e}")
            return None
        finally:
            self.ib.disconnect()
            print("Disconnected from IB")

    # save data to the cloud database AWS dynamically creates variables based on the data
    def create_table(self, df, db_name, table_name):
        try:
            self.create_database(db_name)
            conn = psycopg2.connect(
                host=self.host,
                database=db_name,
                user=self.user,
                password=self.password,
                port=self.port
            )
            cursor = conn.cursor()
            
            # Clean column names
            df.columns = [col.replace(' ', '_').replace('-', '_').lower() for col in df.columns]
            
            # Generate column definitions dynamically based on DataFrame dtypes
            column_definitions = []
            for column, dtype in df.dtypes.items():
                # Map pandas dtypes to PostgreSQL types
                if 'datetime' in str(dtype):
                    sql_type = 'TIMESTAMP'
                elif 'float' in str(dtype):
                    sql_type = 'NUMERIC'  
                elif 'int' in str(dtype):
                    sql_type = 'BIGINT'   
                else:
                    sql_type = 'VARCHAR(255)'
                
                # For stock data, assume ticker is unique if no timestamp
                if column == 'ticker':
                    column_definitions.append(f"\"{column}\" {sql_type} UNIQUE")
                else:
                    column_definitions.append(f"\"{column}\" {sql_type}")
            
            # Create table dynamically
            columns_sql = ', '.join(column_definitions)
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {columns_sql}
            );
            """
            cursor.execute(create_table_query)
            
            # Generate dynamic INSERT query based on DataFrame columns
            columns = df.columns.tolist()
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(f'"{col}"' for col in columns)
            
            # Check if ticker exists for UPSERT
            if 'ticker' in df.columns:
                # Generate dynamic UPDATE clause
                update_clause = ', '.join(
                    f"\"{col}\" = EXCLUDED.\"{col}\""
                    for col in columns
                    if col != 'ticker'
                )
                
                insert_query = f"""
                INSERT INTO {table_name} ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (ticker) 
                DO UPDATE SET 
                    {update_clause};
                """
            else:
                # Simple INSERT if no unique constraint
                insert_query = f"""
                INSERT INTO {table_name} ({columns_str})
                VALUES ({placeholders});
                """
            
            # Insert data
            for _, row in df.iterrows():
                values = tuple(row[col] for col in columns)
                cursor.execute(insert_query, values)
            
            conn.commit()
            print(f"Data successfully saved to {table_name} table in {db_name} database")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Error saving to SQL database: {e}")
            raise e

    # save data to the cloud database AWS dynamically creates variables based on the data but is faster than the previous method
    def bulk_create_table(self, df, db_name, table_name):
        try:
            # Ensure table_name is lowercase to maintain consistency
            table_name = table_name.lower()
            
            self.create_database(db_name)
            engine = create_engine(
                f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{db_name}',
                pool_pre_ping=True
            )
            
            # Clean column names and ensure they're lowercase
            df.columns = [col.replace(' ', '_').replace('-', '_').lower() for col in df.columns]
            
            # Generate column definitions dynamically based on DataFrame dtypes
            column_definitions = []
            for column, dtype in df.dtypes.items():
                if 'datetime' in str(dtype):
                    sql_type = 'TIMESTAMP'
                elif 'float' in str(dtype):
                    if 'volume' in column.lower():
                        sql_type = 'NUMERIC(16,3)'  # Larger precision for volume
                    else:
                        sql_type = 'NUMERIC(10,3)'  # Keep original for other numbers
                elif 'int' in str(dtype):
                    sql_type = 'BIGINT'
                else:
                    sql_type = 'VARCHAR(255)'
                
                if column in ['timestamp', 'ticker']:
                    column_definitions.append(f"{column} {sql_type} UNIQUE")
                else:
                    column_definitions.append(f"{column} {sql_type}")
            
            # Connect and create table with unquoted, lowercase name
            with engine.connect() as conn:
                columns_sql = ', '.join(column_definitions)
                create_table_query = text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {columns_sql}
                );
                """)
                conn.execute(create_table_query)
                
                # Determine unique constraint column
                unique_column = 'timestamp' if 'timestamp' in df.columns else 'ticker' if 'ticker' in df.columns else None
                
                if unique_column:
                    # Temporarily disable index if it exists
                    conn.execute(text(f"DROP INDEX IF EXISTS idx_{table_name}_{unique_column};"))
                
                # Use pandas to_sql with smaller chunks
                df.to_sql(
                    table_name,
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000  # Process 1000 rows at a time
                )
                
                if unique_column:
                    # Recreate the unique index
                    conn.execute(text(f"""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_{unique_column} 
                        ON {table_name}({unique_column});
                    """))
                    
                    # Handle duplicates with an UPSERT
                    conn.execute(text(f"""
                        WITH updated AS (
                            SELECT DISTINCT ON ({unique_column}) *
                            FROM {table_name}
                            ORDER BY {unique_column}, ctid DESC
                        )
                        DELETE FROM {table_name}
                        WHERE ctid NOT IN (SELECT ctid FROM updated);
                    """))
                
                # Commit the transaction
                conn.commit()
                
            print(f"Data successfully saved to {table_name} table in {db_name} database")
            
        except Exception as e:
            print(f"Error saving to SQL database: {e}")
            raise e

    # create a schema in the database if it doesn't already exist and then push a table to the schema
    def create_schema_and_table_dynamic(self, db_name, schema_name, table_name, df):
        """
        Creates a new schema in the specified database if it doesn't already exist,
        creates a table with columns dynamically derived from the df, and bulk inserts the data.
        
        Args:
            db_name (str): Name of the database to create the schema in.
            schema_name (str): Name of the schema to create.
            table_name (str): Name of the table to create.
            df (pd.DataFrame): The DataFrame from which to generate columns and insert data.
        """
        import time
        start_time = time.time()
        
        try:
            print(f"\n📊 Starting data import for {schema_name}.{table_name} ({len(df)} rows)...")
            
            # Create database connection for schema operations
            print("🔌 Connecting to database...")
            conn, cursor = self.connect_to_cloud_database(db_name)
            if not conn or not cursor:
                return

            # 1. Ensure the schema exists
            print("🔍 Checking for existing schema...")
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s;
            """, (schema_name,))
            
            if cursor.fetchone() is None:
                print(f"🏗️  Creating schema '{schema_name}'...")
                cursor.execute(f"CREATE SCHEMA {schema_name};")
                conn.commit()
                print(f"✅ Schema '{schema_name}' created successfully")
            else:
                print(f"✅ Schema '{schema_name}' already exists")
            
            # 3. Clean column names in DataFrame before table creation
            print("🧹 Cleaning column names...")
            df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
            
            # 4. Dynamically generate columns based on DataFrame dtypes
            print("📝 Generating table schema...")
            column_definitions = []
            for column, dtype in df.dtypes.items():
                if 'datetime' in str(dtype):
                    sql_type = 'TIMESTAMP'
                elif 'float' in str(dtype):
                    if 'volume' in column.lower():
                        sql_type = 'NUMERIC(16,3)'  # Larger precision for volume
                    else:
                        sql_type = 'NUMERIC(10,3)'  # Better precision for price data
                elif 'int' in str(dtype):
                    sql_type = 'BIGINT'
                else:
                    sql_type = 'VARCHAR(255)'
                
                if column in ['timestamp', 'datetime', 'date']:
                    column_definitions.append(f"{column} {sql_type} UNIQUE")
                else:
                    column_definitions.append(f"{column} {sql_type}")
            
            # 5. Create table directly using psycopg2
            print(f"🏗️  Creating table '{schema_name}.{table_name}'...")
            columns_sql = ', '.join(column_definitions)
            table_name_lower = table_name.lower()
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.{table_name_lower} (
                {columns_sql}
            );
            """
            cursor.execute(create_table_sql)
            conn.commit()
            
            # Verify table was created successfully
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s;
            """, (schema_name, table_name_lower))
            
            if cursor.fetchone() is None:
                print(f"❌ Failed to create table '{schema_name}.{table_name_lower}'")
                return
            else:
                print(f"✅ Table '{schema_name}.{table_name_lower}' created/verified successfully")
            
            # 6. Determine unique constraint column for efficient upsert
            unique_column = None
            for candidate in ['datetime', 'timestamp', 'date']:
                if candidate in df.columns:
                    unique_column = candidate
                    break
            
            if unique_column:
                print(f"🔑 Using '{unique_column}' as unique identifier")
            
            # 7. Prepare data for bulk insertion using execute_values
            print("🚀 Starting bulk data insertion...")
            insert_start_time = time.time()
            
            # Convert DataFrame to list of tuples for execute_values
            records = df.to_dict('records')
            data_tuples = [tuple(record.values()) for record in records]
            
            # Generate column names string
            columns = df.columns.tolist()
            column_str = ', '.join(columns)
            
            # Create SQL insert statement
            if unique_column:
                # Handle conflict on unique column
                update_cols = [col for col in columns if col != unique_column]
                update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])
                
                insert_query = f"""
                    INSERT INTO {schema_name}.{table_name_lower} ({column_str})
                    VALUES %s
                    ON CONFLICT ({unique_column}) DO UPDATE SET
                    {update_str}
                """
            else:
                insert_query = f"""
                    INSERT INTO {schema_name}.{table_name_lower} ({column_str})
                    VALUES %s
                """
            
            # Execute bulk insert with execute_values
            execute_values(cursor, insert_query, data_tuples, page_size=1000)
            conn.commit()
            
            insert_end_time = time.time()
            insert_duration = insert_end_time - insert_start_time
            
            if unique_column:
                # Create index for better performance
                print("🔍 Creating index...", end='', flush=True)
                index_start_time = time.time()
                index_sql = f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_{schema_name}_{table_name_lower}_{unique_column} 
                ON {schema_name}.{table_name_lower}({unique_column});
                """
                cursor.execute(index_sql)
                conn.commit()
                index_end_time = time.time()
                print(f" Done ({index_end_time - index_start_time:.2f}s)")
            
            end_time = time.time()
            total_duration = end_time - start_time
            avg_rows_per_sec = len(df) / insert_duration if insert_duration > 0 else 0
            
            print(f"✅ Successfully imported {len(df)} rows into {schema_name}.{table_name_lower}")
            print(f"📊 Performance stats:")
            print(f"  ↳ Total time: {total_duration:.2f} seconds")
            print(f"  ↳ Insertion time: {insert_duration:.2f} seconds")
            print(f"  ↳ Average speed: {avg_rows_per_sec:.2f} rows/second")
            
            # Close connection
            cursor.close()
            
        except Exception as e:
            print(f"❌ Error creating schema/table or inserting data: {e}")
            import traceback
            traceback.print_exc()

    # list all databases in the PostgreSQL server
    def list_databases(self):
        """Lists all databases in the PostgreSQL server"""
        try:
            # Connect to default postgres database first
            conn = psycopg2.connect(
                host=self.host,
                database="postgres",  # Connect to default db to list others
                user=self.user,
                password=self.password,
                port=self.port
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Query to list all databases
            cursor.execute("""
                SELECT datname 
                FROM pg_database 
                WHERE datistemplate = false;
            """)
            
            databases = [db[0] for db in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            print("Available databases:")
            for db in sorted(databases):
                print(f"- {db}")
                
            return databases
            
        except Exception as e:
            print(f"Error listing databases: {e}")
            return None

    # list all schemas in a given database
    def list_schemas_in_database(self, db_name):
        """Lists all schemas in the specified database
        
        Args:
            db_name (str): Name of the database to list schemas from
            
        Returns:
            list: List of schema names in the database
        """
        try:
            conn, cursor = self.connect_to_cloud_database(db_name)
            if not conn or not cursor:
                print(f"Could not connect to database {db_name}")
                return []
            
            # Query to list all schemas (excluding system schemas)
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN (
                    'pg_catalog', 'information_schema', 'pg_toast'
                )
                ORDER BY schema_name;
            """)
            
            schemas = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            print(f"\nSchemas in database '{db_name}':")
            for schema in schemas:
                print(f"- {schema}")
                
            return schemas
            
        except Exception as e:
            print(f"Error listing schemas: {e}")
            return []

    # list all industries and subindustries in the Excel file
    def list_all_sectors_industries_and_subindustries(self):
        df = pd.read_excel(excel_file_path)
        print(df)

        if 'GICS Sector' in df.columns:
            unique_sectors = df['GICS Sector'].unique()

            for sector in sorted(unique_sectors):
                if 'GICS Sector' in df.columns:
                    unique_industries = df[df['GICS Sector'] == sector]['GICS Ind Name'].unique()
                    print(f"\n{sector}:")

                    sectorSTR = sector.lower()
                    sectorSTR = sectorSTR.replace(' ', '_')
                    sectorSTR = "equity_sector_" + sectorSTR

                    for industry in sorted(unique_industries):
                        subindustries = df[(df['GICS Sector'] == sector) & (df['GICS Ind Name'] == industry)]['GICS SubInd Name'].unique()
                        print(f"    📁 {industry}")

                        for subindustry in sorted(subindustries):
                            unique_industries = df[(df['GICS Sector'] == sector) & (df['GICS Ind Name'] == industry) & (df['GICS SubInd Name'] == subindustry)]
                            print(f"        🗄️  {subindustry}")

    # list all sectors and industries in the Excel file
    def list_all_sectors_and_industries(self):
        """Lists all sectors and their industries in the Excel file without sub-industries"""
        try:
            df = pd.read_excel(excel_file_path)
            
            if 'GICS Sector' in df.columns:
                unique_sectors = sorted(df['GICS Sector'].unique())
                
                print("\n📊 All Sectors and Industries:")
                for sector in unique_sectors:
                    print(f"\n🔹 {sector}")
                    
                    # Get unique industries for this sector
                    unique_industries = sorted(df[df['GICS Sector'] == sector]['GICS Ind Name'].unique())
                    
                    # Print each industry
                    for industry in unique_industries:
                        print(f"  ├─ {industry}")
                        
                # Print summary
                total_sectors = len(unique_sectors)
                total_industries = len(df['GICS Ind Name'].unique())
                print(f"\nSummary: {total_sectors} sectors and {total_industries} unique industries")
                
                return {sector: sorted(df[df['GICS Sector'] == sector]['GICS Ind Name'].unique()) 
                        for sector in unique_sectors}
            else:
                print("Error: 'GICS Sector' column not found in Excel file")
                return {}
                
        except Exception as e:
            print(f"Error listing sectors and industries: {e}")
            return {}

    # list all subindustries in a given industry
    def list_sub_industries_by_sector_and_industry(self, sector, industry):
        df = pd.read_excel(excel_file_path)
        print(df)
        if 'GICS Sector' in df.columns:
            unique_industries = df[(df['GICS Sector'] == sector) & (df['GICS Ind Name'] == industry)]['GICS SubInd Name'].unique()
            print("\nUnique Information Technology Industries:")
            for industry in sorted(unique_industries):
                print(f"- {industry}")

    def list_stocks_in_sub_industry(self, sector, industry, subindustry):
        df = pd.read_excel(excel_file_path)
        print(df)
        if 'GICS Sector' in df.columns:
            unique_industries = df[(df['GICS Sector'] == sector) & (df['GICS Ind Name'] == industry) & (df['GICS SubInd Name'] == subindustry)]
            print(unique_industries)

    def count_total_items_in_database(self, db_name):
        """
        Counts the total number of rows across all schemas and tables in the specified database.
        
        Args:
            db_name (str): Name of the database to count items in
            
        Returns:
            dict: Dictionary with total count and breakdown by schema and table
        """
        try:
            conn, cursor = self.connect_to_cloud_database(db_name)
            if not conn or not cursor:
                return {"error": "Could not connect to database", "total_count": 0}
            
            # Get all schemas (excluding system schemas)
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN (
                    'pg_catalog', 'information_schema', 'pg_toast'
                )
                ORDER BY schema_name;
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            
            total_count = 0
            results = {"total_count": 0, "schemas": {}}
            
            # For each schema, get all tables and count rows
            for schema in schemas:
                results["schemas"][schema] = {"tables": {}, "schema_total": 0}
                
                # Get all tables in this schema
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """, (schema,))
                
                tables = [row[0] for row in cursor.fetchall()]
                
                # Count rows in each table
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                    count = cursor.fetchone()[0]
                    
                    results["schemas"][schema]["tables"][table] = count
                    results["schemas"][schema]["schema_total"] += count
                    total_count += count
            
            results["total_count"] = total_count
            
            # Print a summary
            print(f"\nTotal items in database '{db_name}': {total_count}")
            for schema, schema_data in results["schemas"].items():
                print(f"  Schema '{schema}': {schema_data['schema_total']} items")
                for table, count in schema_data["tables"].items():
                    print(f"    - Table '{table}': {count} items")
            
            cursor.close()
            conn.close()
            
            return total_count  # Only return the total count instead of a tuple
            
        except Exception as e:
            print(f"Error counting items: {e}")
            return 0  # Return 0 instead of a dictionary in case of error
        
    def get_5y_data(self, ib, symbol):
        try:
            import time
            from ib_insync import Stock, util
            import pandas as pd
            
            print("🔌 Connected to IB")
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Helper function to safely convert to DataFrame and check if empty
            def safe_convert_and_check(bars_data):
                if bars_data is None:
                    return None
                
                # If it's already a DataFrame, just check if it's empty
                if isinstance(bars_data, pd.DataFrame):
                    return None if bars_data.empty else bars_data
                    
                # If it's a BarDataList from IB, convert to DataFrame
                try:
                    df = util.df(bars_data)
                    return None if df.empty else df
                except Exception as e:
                    print(f"Error converting data: {e}")
                    return None
                
            # Rest of your get_date function remains the same
            def get_date(df):
                if df is None or df.empty:
                    return None
                
                if 'date' in df.columns:
                    first_date_str = df['date'].iloc[0]
                    first_date = pd.to_datetime(first_date_str)
                    print(f"First date in data: {first_date}")

                    # Calculate the day before
                    previous_date = first_date.date() - timedelta(days=1)
                    previous_date = str(previous_date).replace('-', '')
                    print(f"Date from the day before: {previous_date}")
                    return previous_date
                else:
                    print("No date column found.")
                    return None

            # YEAR 1
            try:
                bars_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime='',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                # Safely convert to DataFrame
                bars = safe_convert_and_check(bars_raw)
                if bars is None:
                    print(f"⚠️ No valid data for {symbol} in first year")
                    return None
                    
                # Add datetime column and filter
                bars['datetime'] = pd.to_datetime(bars['date'])
                # Keep only data between 9:30 AM and 4:00 PM ET
                bars = bars[
                    (bars['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                    (bars['datetime'].dt.time <= pd.to_datetime('16:00').time())
                ]
                
                if bars.empty:
                    print(f"⚠️ No valid trading hours data for {symbol}")
                    return None
                    
                previous_date = get_date(bars)
                if not previous_date:
                    print(f"⚠️ Could not determine previous date for {symbol}")
                    return bars  # Return what we have so far
                    
            except Exception as e:
                print(f"⚠️ Error fetching first year data for {symbol}: {e}")
                return None

            time.sleep(1)

            # Initialize DataFrames for additional years
            bars2, bars3, bars4, bars5 = None, None, None, None
            
            # YEAR 2
            try:
                bars2_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                # Safely convert to DataFrame
                bars2 = safe_convert_and_check(bars2_raw)
                if bars2 is None:
                    print(f"No data returned for {symbol} in second year - continuing with first year data only")
                else:
                    bars2['datetime'] = pd.to_datetime(bars2['date'])
                    # Filter trading hours
                    bars2 = bars2[
                        (bars2['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars2['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars2.empty:
                        bars2 = None
                        print(f"No valid trading hours data for {symbol} in second year")
                        previous_date2 = None
                    else:
                        previous_date2 = get_date(bars2)
                
            except Exception as e:
                print(f"Error fetching second year data for {symbol}: {e} - continuing with available data")
                previous_date2 = None
                bars2 = None

            time.sleep(1)

            # YEAR 3 - Only proceed if we have previous_date2
            if previous_date2:
                try:
                    bars3_raw = ib.reqHistoricalData(
                        contract, 
                        endDateTime=previous_date2 + ' 18:00:00',
                        durationStr='1 Y', 
                        barSizeSetting='15 mins', 
                        whatToShow='TRADES', 
                        useRTH=False,
                        formatDate=1
                    )
                    
                    bars3 = safe_convert_and_check(bars3_raw)
                    if bars3 is None:
                        print(f"No data returned for {symbol} in third year - continuing with available data")
                        previous_date3 = None
                    else:
                        bars3['datetime'] = pd.to_datetime(bars3['date'])
                        bars3 = bars3[
                            (bars3['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                            (bars3['datetime'].dt.time <= pd.to_datetime('16:00').time())
                        ]
                        
                        if bars3.empty:
                            bars3 = None
                            print(f"No valid trading hours data for {symbol} in third year")
                            previous_date3 = None
                        else:
                            previous_date3 = get_date(bars3)
                    
                except Exception as e:
                    print(f"Error fetching third year data for {symbol}: {e} - continuing with available data")
                    previous_date3 = None
                    bars3 = None
            else:
                previous_date3 = None
                bars3 = None

            time.sleep(1)

            # YEAR 4 - Only proceed if we have previous_date3
            if previous_date3:
                try:
                    bars4_raw = ib.reqHistoricalData(
                        contract, 
                        endDateTime=previous_date3 + ' 18:00:00',
                        durationStr='1 Y', 
                        barSizeSetting='15 mins', 
                        whatToShow='TRADES', 
                        useRTH=False,
                        formatDate=1
                    )
                    
                    bars4 = safe_convert_and_check(bars4_raw)
                    if bars4 is None:
                        print(f"No data returned for {symbol} in fourth year - continuing with available data")
                        previous_date4 = None
                    else:
                        bars4['datetime'] = pd.to_datetime(bars4['date'])
                        bars4 = bars4[
                            (bars4['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                            (bars4['datetime'].dt.time <= pd.to_datetime('16:00').time())
                        ]
                        
                        if bars4.empty:
                            bars4 = None
                            print(f"No valid trading hours data for {symbol} in fourth year")
                            previous_date4 = None
                        else:
                            previous_date4 = get_date(bars4)
                    
                except Exception as e:
                    print(f"Error fetching fourth year data for {symbol}: {e} - continuing with available data")
                    previous_date4 = None
                    bars4 = None
            else:
                previous_date4 = None
                bars4 = None

            time.sleep(1)

            # YEAR 5 - Only proceed if we have previous_date4
            if previous_date4:
                try:
                    bars5_raw = ib.reqHistoricalData(
                        contract, 
                        endDateTime=previous_date4 + ' 18:00:00',
                        durationStr='1 Y', 
                        barSizeSetting='15 mins', 
                        whatToShow='TRADES', 
                        useRTH=False,
                        formatDate=1
                    )
                    
                    bars5 = safe_convert_and_check(bars5_raw)
                    if bars5 is None:
                        print(f"No data returned for {symbol} in fifth year - continuing with available data")
                    else:
                        bars5['datetime'] = pd.to_datetime(bars5['date'])
                        bars5 = bars5[
                            (bars5['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                            (bars5['datetime'].dt.time <= pd.to_datetime('16:00').time())
                        ]
                        
                        if bars5.empty:
                            bars5 = None
                            print(f"No valid trading hours data for {symbol} in fifth year")
                    
                except Exception as e:
                    print(f"Error fetching fifth year data for {symbol}: {e} - continuing with available data")
                    bars5 = None
            else:
                bars5 = None

            # Prepare list of DataFrames to concatenate
            # This is where the error was occurring - now we've already ensured all are DataFrames
            dfs_to_concat = []
            for i, df in enumerate([bars, bars2, bars3, bars4, bars5], 1):
                if df is not None and not df.empty:
                    dfs_to_concat.append(df)
                    print(f"✅ Year {i} data will be included: {len(df)} rows")
                else:
                    print(f"❌ Year {i} data not available")
            
            if not dfs_to_concat:
                print(f"⚠️ No valid data frames to concatenate for {symbol}")
                return None
            
            # Concatenate the DataFrames and sort by datetime
            print(f"🔄 Combining data from {len(dfs_to_concat)} years...")
            combined_bars = pd.concat(dfs_to_concat, ignore_index=True)
            combined_bars = combined_bars.sort_values('datetime').reset_index(drop=True)
            # Remove any duplicate rows based on datetime
            combined_bars = combined_bars.drop_duplicates(subset='datetime', keep='first')
            print(f"📊 Combined and deduplicated bars for {symbol}: {len(combined_bars)} records")
            
            if len(combined_bars) > 0:
                print(combined_bars.head())
                if len(combined_bars) > 5:
                    print("...")
                    print(combined_bars.tail())
            else:
                print("No data available.")
            
            return combined_bars
            
        except Exception as e:
            print(f"⚠️ Unexpected error in get_5y_data for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_tickers_by_sector_and_industry(self, sector, industry):
        """
        Retrieves all tickers that match a specific sector and industry.
        
        Args:
            sector (str): The GICS Sector to filter by
            industry (str): The GICS Industry Name to filter by
            
        Returns:
            list: List of ticker symbols matching the criteria, with 'US Equity' stripped
        """
        try:
            # Read the Excel file
            df = pd.read_excel(excel_file_path)
            
            # Filter by sector and industry
            filtered_df = df[(df['GICS Sector'] == sector) & (df['GICS Ind Name'] == industry)]
            
            # Get unique tickers
            if 'Ticker' in filtered_df.columns:
                tickers = filtered_df['Ticker'].unique().tolist()
            elif 'ticker' in filtered_df.columns:
                tickers = filtered_df['ticker'].unique().tolist()
            elif 'Symbol' in filtered_df.columns:
                tickers = filtered_df['Symbol'].unique().tolist()
            elif 'symbol' in filtered_df.columns:
                tickers = filtered_df['symbol'].unique().tolist()
            else:
                # If none of the expected ticker columns are found, try to identify a possible ticker column
                possible_ticker_columns = [col for col in filtered_df.columns if 'tick' in col.lower() or 'symb' in col.lower()]
                if possible_ticker_columns:
                    tickers = filtered_df[possible_ticker_columns[0]].unique().tolist()
                else:
                    print(f"Could not find ticker column in Excel file. Available columns: {', '.join(filtered_df.columns)}")
                    return []
            
            # Strip " US Equity" from tickers
            cleaned_tickers = [ticker.replace(' US Equity', '') if isinstance(ticker, str) else ticker for ticker in tickers]
            
            # Print the tickers with count
            print(f"\nFound {len(cleaned_tickers)} tickers in {sector} sector, {industry} industry:")
            for i, ticker in enumerate(sorted(cleaned_tickers)):
                print(f"{i+1}. {ticker}")
            
            return cleaned_tickers
            
        except Exception as e:
            print(f"Error finding tickers: {e}")
            return []

    def safe_convert_and_check(self, bars_data):
        """
        Safely converts IB API BarDataList to DataFrame and checks if it's empty.
        
        Args:
            bars_data: Data returned from IB API (either BarDataList or DataFrame)
            
        Returns:
            DataFrame or None: Converted DataFrame if valid data exists, otherwise None
        """
        if bars_data is None:
            return None
        
        # If it's already a DataFrame, just check if it's empty
        if isinstance(bars_data, pd.DataFrame):
            return None if bars_data.empty else bars_data
            
        # If it's a BarDataList from IB, convert to DataFrame
        try:
            df = util.df(bars_data)
            return None if df.empty else df
        except Exception as e:
            print(f"Error converting data: {e}")
            return None

    def create_schema(self, db_name, schema_name):
        """
        Creates a new schema in the specified database if it doesn't already exist.
        
        Args:
            db_name (str): Name of the database to create the schema in.
            schema_name (str): Name of the schema to create.
            
        Returns:
            bool: True if schema exists or was created successfully, False otherwise.
        """
        try:
            print(f"\n🔍 Checking for schema '{schema_name}' in database '{db_name}'...")
            
            # Create database connection
            conn, cursor = self.connect_to_cloud_database(db_name)
            if not conn or not cursor:
                print(f"❌ Could not connect to database {db_name}")
                return False

            # Check if schema exists
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s;
            """, (schema_name,))
            
            if cursor.fetchone() is None:
                print(f"🏗️  Creating schema '{schema_name}'...")
                cursor.execute(f"CREATE SCHEMA {schema_name};")
                conn.commit()
                print(f"✅ Schema '{schema_name}' created successfully")
            else:
                print(f"✅ Schema '{schema_name}' already exists")
            
            cursor.close()
            return True
            
        except Exception as e:
            print(f"❌ Error creating schema: {e}")
            import traceback
            traceback.print_exc()
            return False

def connect_to_ib():
    ib = IB()
    if ib.isConnected():
        ib.disconnect()

    connected = False

    for port in [4002, 7497]:
        for clientId in range(7):  # Try client IDs from 0 to 6
            try:
                ib.connect('127.0.0.1', port, clientId=clientId)
                connected = True
                print(f"🌐 Connected successfully on port {port} with clientId {clientId}")
                break  # Break out of the clientId loop
            except Exception as e:
                print(f"🚨 Failed to connect on port {port} with clientId {clientId}: {e}")
                pass
        
        if connected:
            break  # Break out of the port loop if we're connected
    
    if not connected:
        print("⛔ Could not connect to IB on any port with any clientId")
        return None

    return ib

def clean_list(items):
    """
    Takes a list of items, removes duplicates, and returns a sorted clean list.
    
    Args:
        items (list): List of items that may contain duplicates
        
    Returns:
        list: Sorted list with duplicates removed
    """
    # Convert to set to remove duplicates, then back to list and sort
    clean_items = sorted(list(set(items)))
    
    # Print summary
    print(f"Original list had {len(items)} items")
    print(f"After removing duplicates: {len(clean_items)} items")
    
    return clean_items

def process_text_to_list(text):
    """
    Process text input and convert it to a clean Python list with duplicates removed.
    
    Args:
        text (str): Text containing items, can be separated by commas, newlines, or other delimiters
        
    Returns:
        list: Clean Python list with duplicates removed
    """
    # First try to split by newlines (common for copy-paste from spreadsheets)
    items = [item.strip() for item in text.split('\n') if item.strip()]
    
    # If only one item was found, try splitting by commas
    if len(items) <= 1:
        items = [item.strip() for item in text.replace('\n', ',').split(',') if item.strip()]
    
    # If still only one item or none, check if text has semicolons
    if len(items) <= 1 and ';' in text:
        items = [item.strip() for item in text.replace('\n', ';').split(';') if item.strip()]
    
    # Remove any empty strings and duplicates
    return clean_list(items)


def run(sector, industry):
    # create list of industries here
    db = IBKRDatabase()
    ib = connect_to_ib()
    try:
        tickers = db.get_tickers_by_sector_and_industry(sector, industry)
        print(tickers)

        industry = industry.replace(' ', '_')
        industry = industry.lower()
        industry = industry.replace('&', 'and')
        industry = industry.replace('-', '_')
        industry = industry.replace(',', '_')
        industry = industry + '_prices'
        print(industry)

        # Find TTD in the list and start from there
        try:
            start_index = tickers.index('SURG')
            tickers_to_process = tickers[start_index:]
        except ValueError:
            print("STRT not found in the ticker list. Starting from the beginning.")
            tickers_to_process = tickers

        for ticker in tickers_to_process:
            print(f"\nProcessing ticker: {ticker}")
            data = db.get_5y_data(ib, ticker)
            
            if data is not None and not data.empty:
                print(f"🚀 Retrieved {len(data)} rows of data for {ticker}")
                sector = sector.replace(' ', '_')
                sector = sector.replace(' ', '_')
                sector = sector.lower()
                sector = sector.replace('&', 'and')
                sector = sector.replace('-', '_')
                sector = sector.replace(',', '_')
                db.create_schema_and_table_dynamic(f'equity_sector_{sector}_prices', industry, ticker, data)
            else:
                print(f"⚠️ Could not retrieve data for {ticker} - skipping")
                continue
    finally:
        # Close all database connections when done
        db.close_connection()
        ib.disconnect()


def print_etf_database_contents():
    """Print all contents of the etf_data database"""
    db = IBKRDatabase()
    conn, cursor = db.connect_to_cloud_database("etf_data")
    
    if not conn or not cursor:
        print("❌ Failed to connect to etf_data database")
        return
    
    # Get all schemas in the database
    cursor.execute("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name;
    """)
    schemas = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📊 ETF Database Contents - {len(schemas)} schemas found")
    
    # For each schema, get all tables
    for schema in schemas:
        print(f"\n🔷 Schema: {schema}")
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """, (schema,))
        tables = [row[0] for row in cursor.fetchall()]
        
        # For each table, print contents
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
            count = cursor.fetchone()[0]
            print(f"  📋 Table: {table} - {count} rows")
            
            # Print schema of table
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
            """, (schema, table))
            columns = cursor.fetchall()
            
            print("    Columns:")
            for col, dtype in columns:
                print(f"      - {col} ({dtype})")
            
            # Print sample data (first 5 rows)
            if count > 0:
                cursor.execute(f"SELECT * FROM {schema}.{table} LIMIT 5")
                rows = cursor.fetchall()
                
                print("    Sample data:")
                for row in rows:
                    print(f"      {row}")
                    
            print("\n")
    
    # Close connection
    cursor.close()
    conn.close()

def get_etf_tickers(db_instance):
    """
    Retrieve all ETF tickers from etf_data database organized by schema and category
    
    Args:
        db_instance: An instance of IBKRDatabase class
    
    Returns:
        dict: Dictionary with schema as keys and lists of (category, ticker) tuples as values
    """
    conn, cursor = db_instance.connect_to_cloud_database("etf_data")
    
    if not conn or not cursor:
        print("❌ Failed to connect to etf_data database")
        return {}
    
    # Get all schemas in the database
    cursor.execute("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name;
    """)
    schemas = [row[0] for row in cursor.fetchall()]
    
    etf_tickers = {}
    
    # For each schema, get all tables (categories) and their tickers
    for schema in schemas:
        etf_tickers[schema] = []
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """, (schema,))
        tables = [row[0] for row in cursor.fetchall()]
        
        # For each table (category), get tickers
        for table in tables:
            # Verify the table has a ticker column (adjust if column name is different)
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
                AND column_name IN ('ticker', 'symbol', 'etf_ticker');
            """, (schema, table))
            
            ticker_columns = [row[0] for row in cursor.fetchall()]
            
            if ticker_columns:
                ticker_column = ticker_columns[0]  # Use the first found ticker column
                
                # Get tickers from this category
                cursor.execute(f"SELECT {ticker_column} FROM {schema}.{table}")
                category_tickers = [row[0] for row in cursor.fetchall()]
                
                # Add to our collection with category information
                for ticker in category_tickers:
                    if ticker:  # Ensure we don't add empty tickers
                        # Clean the ticker symbol if needed (remove spaces, etc.)
                        cleaned_ticker = ticker.strip() if isinstance(ticker, str) else ticker
                        etf_tickers[schema].append((table, cleaned_ticker))
                        
                print(f"  Found {len(category_tickers)} tickers in {schema}.{table}")
    
    # Print summary
    total_tickers = sum(len(tickers) for tickers in etf_tickers.values())
    print(f"\n✅ Retrieved {total_tickers} ETF tickers from {len(schemas)} schemas")
    
    # Close connection
    cursor.close()
    
    return etf_tickers

def run_etfs(start_ticker=None):
    """
    Process ETFs similar to how stocks are processed in the run() function.
    Fetches data for each ETF and stores it in the etf_prices database.
    
    Args:
        start_ticker (str, optional): If provided, processing will start from this ticker.
    """
    db = IBKRDatabase()
    ib = connect_to_ib()
    
    try:
        # Get all ETF tickers organized by schema and category
        print("🔍 Retrieving ETF tickers from database...")
        etf_tickers_by_schema = get_etf_tickers(db)
        
        if not etf_tickers_by_schema:
            print("❌ No ETF tickers found")
            return
        
        # Track if we should start processing
        found_start_ticker = start_ticker is None
        
        # Process each schema
        for schema, tickers_with_categories in etf_tickers_by_schema.items():
            print(f"\n🔷 Processing {len(tickers_with_categories)} tickers in schema: {schema}")
            
            # Create a new schema name for etf_prices database
            # Convert from 'alternative_etfs' to just 'alternative' etc.
            base_schema = schema.replace('_etfs', '')
            target_schema = f"{base_schema}_etfs_prices"
            
            # Create the schema in etf_prices database
            db.create_database("etf_prices")
            db.create_schema("etf_prices", target_schema)
            
            # Process each ticker in this schema
            for category, ticker in tickers_with_categories:
                # Skip until we find the start ticker
                if not found_start_ticker:
                    if ticker == start_ticker:
                        found_start_ticker = True
                        print(f"\n🚀 Resuming from ticker: {ticker}")
                    else:
                        print(f"⏭️  Skipping {ticker} (waiting to reach {start_ticker})")
                        continue
                
                print(f"\n📈 Processing ETF: {ticker} (Category: {category})")
                
                # Make sure we're still connected to IB
                if not ib.isConnected():
                    print("🔄 Reconnecting to IB...")
                    ib = connect_to_ib()
                    if not ib:
                        print("❌ Failed to reconnect to IB - aborting")
                        return
                
                # Fetch 5 years of data
                data = db.get_5y_data(ib, ticker)
                
                if data is not None and not data.empty:
                    print(f"✅ Retrieved {len(data)} rows of data for {ticker}")
                    
                    # Create table name based on category (similar to industry in stocks)
                    category_table = category.lower()
                    category_table = category_table.replace(' ', '_')
                    category_table = category_table.replace('&', 'and')
                    category_table = category_table.replace('-', '_')
                    category_table = category_table.replace(',', '_')
                    
                    # Create schema and table with the data
                    db.create_schema_and_table_dynamic("etf_prices", target_schema, ticker, data)
                else:
                    print(f"⚠️ Could not retrieve data for {ticker} - skipping")
                    continue
    
    finally:
        # Close all database connections when done
        db.close_connection()
        if ib and ib.isConnected():
            ib.disconnect()
            print("Disconnected from IB")


            