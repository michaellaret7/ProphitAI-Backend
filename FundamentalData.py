import requests
import json
from tabulate import tabulate
import pandas as pd
import sys
import os
import psycopg2
from ib_insync import *
from sqlalchemy import create_engine, text

api_key = '7b14137a-24fa-45d3-a752-6889558f551f'
ticker = "AAPL"
period = "quarterly"
limit = "100"

def get_financial_data(ticker, period, limit):
    """Fetch financial data from the API and return formatted results"""
    # First API call - Get income statements, balance sheets, and cash flow statements
    financials_url = "https://api.financialdatasets.ai/financials"
    
    querystring = {"ticker": ticker, "period": period, "limit": limit}
    headers = {"X-API-KEY": api_key}
    
    financials_response = requests.request("GET", financials_url, headers=headers, params=querystring)
    financials_data = json.loads(financials_response.text)
    
    # Second API call - Get financial metrics
    metrics_url = "https://api.financialdatasets.ai/financial-metrics"
    
    metrics_response = requests.request("GET", metrics_url, headers=headers, params=querystring)
    metrics_data = json.loads(metrics_response.text)
    
    # Combine the data
    combined_data = financials_data
    if "financial_metrics" in metrics_data:
        combined_data["financial_metrics"] = metrics_data["financial_metrics"]
    
    # Display nicely formatted JSON
    print("\n=== COMPLETE FINANCIAL DATA ===\n")
    print(json.dumps(combined_data, indent=2))

    return combined_data

def read_sector_excel(filename="finalSectorSheet.xlsx"):
    """
    Read an Excel file from the parent documents folder.
    
    Args:
        filename (str): Name of the Excel file to read
        
    Returns:
        pd.DataFrame: DataFrame containing the Excel data
    """
    try:
        # Navigate up one directory level to access the documents folder
        # assuming the current working directory is Documents/ProhpitAI
        file_path = os.path.join("..", filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            print(f"Current working directory: {os.getcwd()}")
            return None
            
        # Read the Excel file
        df = pd.read_excel(file_path)
        print(f"✅ Successfully loaded {filename}")
        print(f"📊 Shape: {df.shape}")
        
        # Display the first few rows
        print("\nPreview of the data:")
        print(df.head())
        
        return df
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return None
    
def get_ib_historical_data(ticker):
    """
    Get the most recent closing price for a ticker from Interactive Brokers.
    
    Args:
        ticker (str): The ticker symbol to get data for
        
    Returns:
        float: The most recent closing price, or None if no data is available
    """
    from ib_insync import IB, Stock
    from datetime import datetime, timedelta
    
    try:
        # Connect to IB Gateway
        print(f"Connecting to IB Gateway on port 4002...")
        ib = IB()
        ib.connect('127.0.0.1', '4002', clientId=3)
        
        # Create contract for the ticker (assuming US stock)
        contract = Stock(ticker, 'SMART', 'USD')
        
        # Request historical data
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr='2 D',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        
        # Extract the most recent close price
        if bars and len(bars) > 0:
            # Get the last bar (most recent)
            most_recent_bar = bars[-1]
            close_price = most_recent_bar.close
            print(f"✅ Most recent close price for {ticker}: {close_price}")
            return close_price
        else:
            print(f"⚠️ No historical data retrieved for {ticker}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving historical data: {e}")
        return None
        
    finally:
        # Disconnect from IB
        ib.disconnect()


get_ib_historical_data('XLF')

def get_news(ticker, start_date, end_date, limit):
    url = "https://api.financialdatasets.ai/news"

    querystring = {"ticker": ticker, "start_date": start_date, "end_date": end_date, "limit": limit}

    headers = {"X-API-KEY": "7b14137a-24fa-45d3-a752-6889558f551f"}

    response = requests.request("GET", url, headers=headers, params=querystring)

    print(response.text)


class PushFundamentalDataToDB:
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

    def close_connection(self, db_name=None):
        """Explicitly close database connections"""
        if db_name and db_name in self.conn_pool and self.conn_pool[db_name]:
            try:
                self.conn_pool[db_name].close()
                self.conn_pool[db_name] = None
                print(f"✅ Closed connection to {db_name}")
            except Exception as e:
                print(f"⚠️ Error closing connection to {db_name}: {e}")
        elif db_name is None:
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
                    print(f"✅ Database '{db_name}' created successfully")
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
        
        conn = None
        cursor = None
        
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
                elif 'float' in str(dtype) or 'int' in str(dtype):
                    # Use NUMERIC without precision/scale constraints for unlimited size
                    sql_type = 'NUMERIC'  # Removed the (30,3) constraint to allow arbitrarily large numbers
                else:
                    sql_type = 'VARCHAR(255)'
                
                if column in ['timestamp', 'datetime', 'date']:
                    column_definitions.append(f"{column} {sql_type} UNIQUE")
                else:
                    column_definitions.append(f"{column} {sql_type}")
            
            # Add debug output to see column types
            print(f"Column definitions preview for {schema_name}.{table_name} (first 5):")
            for i, col_def in enumerate(column_definitions[:5]):
                print(f"  {col_def}")
            if len(column_definitions) > 5:
                print(f"  ... and {len(column_definitions)-5} more columns")
            
            # Use unquoted lower case for table name in creation
            table_name_lower = table_name.lower()
            
            # Check if table exists, and drop it if it's a cash flow statement table or has _cash_flow_ in name
            # This ensures we recreate with proper column types
            if 'cash_flow' in table_name_lower or 'cashflow' in table_name_lower:
                print(f"🔄 Checking and potentially rebuilding cash flow table...")
                cursor.execute(f"""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = '{schema_name}' AND table_name = '{table_name_lower}'
                """)
                if cursor.fetchone():
                    print(f"🗑️  Dropping existing cash flow table to recreate with proper column precision...")
                    cursor.execute(f"DROP TABLE {schema_name}.{table_name_lower}")
                    conn.commit()
            
            # 5. Create table directly using psycopg2 (not SQLAlchemy) to ensure it exists
            print(f"🏗️  Creating table '{schema_name}.{table_name}'...")
            columns_sql = ', '.join(column_definitions)
            
            table_create_sql = f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.{table_name_lower} (
                    {columns_sql}
                );
            """
            cursor.execute(table_create_sql)
            conn.commit()
            
            print(f"✅ Table '{schema_name}.{table_name_lower}' created/verified successfully")
            
            # 6. Determine unique constraint column for efficient upsert
            unique_column = None
            for candidate in ['datetime', 'timestamp', 'date']:
                if candidate in df.columns:
                    unique_column = candidate
                    break
            
            if unique_column:
                print(f"🔑 Using '{unique_column}' as unique identifier")
            
            # Close the psycopg2 connection as we'll use SQLAlchemy for data insertion
            cursor.close()
            conn.close()
            
            # 7. Create SQLAlchemy engine for efficient data insertion
            print("🔧 Creating database engine...")
            engine = create_engine(
                f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{db_name}',
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            
            # 8. Bulk insertion with progress reporting
            print("🚀 Starting data insertion...")
            records = df.to_dict('records')
            chunk_size = 5000
            total_chunks = (len(records) + chunk_size - 1) // chunk_size
            
            insert_start_time = time.time()
            
            if unique_column:
                # Build column update statement for all columns except the unique one
                update_cols = [col for col in df.columns if col != unique_column]
                update_stmt = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])
                
                # Process in chunks with progress reporting
                for i in range(0, len(records), chunk_size):
                    chunk_num = i // chunk_size + 1
                    chunk = records[i:i+chunk_size]
                    chunk_start = time.time()
                    if chunk:
                        print(f"  ↳ Inserting chunk {chunk_num}/{total_chunks} ({len(chunk)} rows)...", end='', flush=True)
                        
                        # Generate the INSERT statement with ON CONFLICT DO UPDATE
                        # Important: Use lowercase table name to match what PostgreSQL created
                        column_names = df.columns.tolist()
                        insert_stmt = text(f"""
                            INSERT INTO {schema_name}.{table_name_lower} ({', '.join(column_names)})
                            VALUES ({', '.join([':' + col for col in column_names])})
                            ON CONFLICT ({unique_column}) DO UPDATE SET
                            {update_stmt}
                        """)
                        
                        # Execute with the chunk using a fresh connection
                        with engine.begin() as trans_conn:
                            trans_conn.execute(insert_stmt, chunk)
                            
                        chunk_end = time.time()
                        print(f" Done ({chunk_end - chunk_start:.2f}s)")
                
                print("✅ All chunks committed successfully")
                
            else:
                # If no unique column, use simple insert
                for i in range(0, len(records), chunk_size):
                    chunk_num = i // chunk_size + 1
                    chunk = records[i:i+chunk_size]
                    chunk_start = time.time()
                    if chunk:
                        print(f"  ↳ Inserting chunk {chunk_num}/{total_chunks} ({len(chunk)} rows)...", end='', flush=True)
                        
                        # Use lowercase table name
                        column_names = df.columns.tolist()
                        insert_stmt = text(f"""
                            INSERT INTO {schema_name}.{table_name_lower} ({', '.join(column_names)})
                            VALUES ({', '.join([':' + col for col in column_names])})
                        """)
                        
                        with engine.begin() as trans_conn:
                            trans_conn.execute(insert_stmt, chunk)
                            
                        chunk_end = time.time()
                        print(f" Done ({chunk_end - chunk_start:.2f}s)")
                
                print("✅ All chunks committed successfully")
            
            insert_end_time = time.time()
            insert_duration = insert_end_time - insert_start_time
            
            if unique_column:
                # Create index with direct psycopg2 connection for better control
                print("🔍 Creating index...", end='', flush=True)
                conn, cursor = self.connect_to_cloud_database(db_name)
                index_start_time = time.time()
                index_sql = f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_{schema_name}_{table_name_lower}_{unique_column} 
                ON {schema_name}.{table_name_lower}({unique_column});
                """
                cursor.execute(index_sql)
                conn.commit()
                index_end_time = time.time()
                print(f" Done ({index_end_time - index_start_time:.2f}s)")
                
                cursor.close()
                conn.close()
            
            end_time = time.time()
            total_duration = end_time - start_time
            avg_rows_per_sec = len(df) / insert_duration if insert_duration > 0 else 0
            
            print(f"✅ Successfully imported {len(df)} rows into {schema_name}.{table_name_lower}")
            print(f"📊 Performance stats:")
            print(f"  ↳ Total time: {total_duration:.2f} seconds")
            print(f"  ↳ Insertion time: {insert_duration:.2f} seconds")
            print(f"  ↳ Average speed: {avg_rows_per_sec:.2f} rows/second")
            
        except Exception as e:
            print(f"❌ Error creating schema/table or inserting data: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Ensure connections are properly closed
            if cursor and not isinstance(cursor, psycopg2.extensions.cursor):
                try:
                    cursor.close()
                except:
                    pass
                    
            # We don't close the connection here as it's now managed in the connection pool
    

def upload_sector_fundamentals(sector, industry, period="quarterly", limit="100", db_name='equity_sector_communication_services_fundamentals'):
    """
    Fetches and uploads fundamental data for all companies in a given sector and industry.
    
    Args:
        sector (str): The sector name (e.g., "Communication Services")
        industry (str): The industry name (e.g., "Diversified Telecommunication Services")
        period (str): Period frequency ("quarterly" or "annual")
        limit (str): Number of periods to retrieve (default: "100" for extensive historical data)
        db_name (str): Database name to use
    """
    print(f"\n🔍 Processing fundamental data for {sector} - {industry}")
    
    # Create database handler and ensure database exists
    db_handler = PushFundamentalDataToDB()
    try:
        db_handler.create_database(db_name)
        
        # Format schema name based on industry
        schema_name = industry.lower().replace(' ', '_').replace('&', 'and').replace(',', '_')
        
        # Read sector Excel and get tickers
        sector_df = read_sector_excel()
        if sector_df is None:
            print("❌ Failed to load sector data.")
            return
        
        # Filter by sector and industry
        filtered_df = sector_df[(sector_df['GICS Sector'] == sector) & (sector_df['GICS Ind Name'] == industry)]
        
        if filtered_df.empty:
            print(f"⚠️ No companies found in {sector} sector, {industry} industry.")
            return
        
        # Get ticker column (handle different possible column names)
        ticker_col = None
        for col in ['ticker', 'Ticker', 'Symbol', 'symbol']:
            if col in filtered_df.columns:
                ticker_col = col
                break
        
        if ticker_col is None:
            print("❌ Could not find ticker column in sector data.")
            return
        
        # Get list of tickers and clean them
        tickers = filtered_df[ticker_col].unique().tolist()
        tickers = [t.replace(' US Equity', '') if isinstance(t, str) else t for t in tickers]
        
        print(f"📈 Found {len(tickers)} companies in {sector} sector, {industry} industry")
        
        # Process each ticker
        for i, ticker in enumerate(tickers):
            print(f"\n[{i+1}/{len(tickers)}] Processing {ticker}...")
            try:
                # Get financial data
                financial_data = get_financial_data(ticker, period, limit)
                
                # Process each financial statement type directly
                if 'financials' in financial_data:
                    financials = financial_data['financials']
                    
                    # Process income statements
                    if 'income_statements' in financials and financials['income_statements']:
                        print(f"💰 Uploading income statements for {ticker}...")
                        income_df = pd.DataFrame(financials['income_statements'])
                        # Fill any NaN values with None for proper NULL handling in PostgreSQL
                        income_df = income_df.replace({pd.NA: None, float('nan'): None})
                        income_df['date'] = pd.to_datetime(income_df['calendar_date'])
                        db_handler.create_schema_and_table_dynamic(
                            db_name, schema_name, f"{ticker}_income_statements", income_df
                        )
                    
                    # Process balance sheets
                    if 'balance_sheets' in financials and financials['balance_sheets']:
                        print(f"📑 Uploading balance sheets for {ticker}...")
                        balance_df = pd.DataFrame(financials['balance_sheets'])
                        balance_df = balance_df.replace({pd.NA: None, float('nan'): None})
                        balance_df['date'] = pd.to_datetime(balance_df['calendar_date'])
                        db_handler.create_schema_and_table_dynamic(
                            db_name, schema_name, f"{ticker}_balance_sheets", balance_df
                        )
                    
                    # Process cash flow statements
                    if 'cash_flow_statements' in financials and financials['cash_flow_statements']:
                        print(f"💵 Uploading cash flow statements for {ticker}...")
                        cashflow_df = pd.DataFrame(financials['cash_flow_statements'])
                        cashflow_df = cashflow_df.replace({pd.NA: None, float('nan'): None})
                        cashflow_df['date'] = pd.to_datetime(cashflow_df['calendar_date'])
                        db_handler.create_schema_and_table_dynamic(
                            db_name, schema_name, f"{ticker}_cash_flow_statements", cashflow_df
                        )
                
                # Process financial metrics
                if 'financial_metrics' in financial_data and financial_data['financial_metrics']:
                    print(f"📊 Uploading financial metrics for {ticker}...")
                    metrics_df = pd.DataFrame(financial_data['financial_metrics'])
                    metrics_df = metrics_df.replace({pd.NA: None, float('nan'): None})
                    metrics_df['date'] = pd.to_datetime(metrics_df['calendar_date'])
                    db_handler.create_schema_and_table_dynamic(
                        db_name, schema_name, f"{ticker}_financial_metrics", metrics_df
                    )
                
                print(f"✅ Completed processing {ticker}")
                
                # Pause between API calls to avoid rate limits
                if i < len(tickers) - 1:
                    print("⏳ Pausing before next company...")
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Error processing {ticker}: {e}")
        
        print(f"\n🎉 Completed fundamental data processing for {len(tickers)} companies in {industry}!")
        
    finally:
        # Properly close all database connections when done
        db_handler.close_connection()


# upload_sector_fundamentals("Communication Services", "Diversified Telecommunication Services")
# upload_sector_fundamentals("Communication Services", "Entertainment")
# upload_sector_fundamentals("Communication Services", "Interactive Media & Services")
# upload_sector_fundamentals("Communication Services", "Media")
# upload_sector_fundamentals("Communication Services", "Wireless Telecommunication Services")

# Add Consumer Discretionary sector uploads

# upload_sector_fundamentals("Consumer Discretionary", "Automobile Components", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Automobiles", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Broadline Retail", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Distributors", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Diversified Consumer Services", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Hotels, Restaurants & Leisure", db_name='equity_sector_consumer_discretionary_fundamentals') 
# upload_sector_fundamentals("Consumer Discretionary", "Household Durables", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Leisure Products", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Specialty Retail", db_name='equity_sector_consumer_discretionary_fundamentals')
# upload_sector_fundamentals("Consumer Discretionary", "Textiles, Apparel & Luxury Goods", db_name='equity_sector_consumer_discretionary_fundamentals') 

# df = read_sector_excel()

# if df is not None:
#     # Create a dictionary to store sector -> industries mapping
#     sectors_and_industries = {}
#     for sector in df['GICS Sector'].unique():
#         sector_df = df[df['GICS Sector'] == sector]
#         industries = sector_df['GICS Ind Name'].unique().tolist()
#         sectors_and_industries[sector] = industries
    
#     # Remove Communication Services and Consumer Discretionary sectors
#     sectors_and_industries.pop('Communication Services', None)
#     sectors_and_industries.pop('Consumer Discretionary', None)
    
#     # Print the dictionary for verification
#     print("\n=== SECTORS AND INDUSTRIES DICTIONARY (without Communication Services and Consumer Discretionary) ===\n")
#     # print(sectors_and_industries)
# else:
#     print("❌ Unable to create sectors dictionary - Excel file could not be loaded")

# # Flag to determine when to start processing
# start_processing = False
# # Add a resume point for ACLX in Biotechnology
# resume_ticker = "CBT"
# resume_industry = "Chemicals"

# # Print each sector-industry pair
# for sector, industries in sectors_and_industries.items():
#     for industry in industries:
#         if industry == resume_industry:
#             start_processing = True
#             print(f"Starting processing from {sector} - {industry}")
        
#         # Only process if we've reached or passed the resume industry
#         if start_processing:
#             dbName = f'equity_sector_{sector.lower().replace(" ", "_")}_fundamentals'
#             print(f"Checking {sector} - {industry} for processing...")
            
#             # Get tickers for this industry to check for resume point
#             sector_df = df[(df['GICS Sector'] == sector) & (df['GICS Ind Name'] == industry)]
            
#             # Get ticker column (handle different possible column names)
#             ticker_col = None
#             for col in ['ticker', 'Ticker', 'Symbol', 'symbol']:
#                 if col in sector_df.columns:
#                     ticker_col = col
#                     break
            
#             if ticker_col is not None:
#                 tickers = sector_df[ticker_col].unique().tolist()
#                 tickers = [t.replace(' US Equity', '') if isinstance(t, str) else t for t in tickers]
                
#                 # If we're at the resume industry, check if we need to skip to specific ticker
#                 if industry == resume_industry and resume_ticker in tickers:
#                     # Get index of resume ticker
#                     resume_index = tickers.index(resume_ticker)
#                     # Slice the list to start from resume_ticker
#                     tickers = tickers[resume_index:]
#                     print(f"✅ Resuming from {resume_ticker} in {industry} (skipped {resume_index} previous tickers)")
                    
#                     # Reset resume ticker to avoid checking in subsequent industries
#                     resume_ticker = None
#                 elif industry == resume_industry and resume_ticker not in tickers:
#                     print(f"⚠️ Resume ticker {resume_ticker} not found in {industry}. Processing all tickers in this industry.")
#                     resume_ticker = None
                    
#                 # Process this industry
#                 print(f"Uploading {sector} - {industry} with {len(tickers)} tickers to {dbName}")
                
#                 # Process each ticker individually to better manage connections
#                 for ticker in tickers:
#                     print(f"\n🔍 Processing {ticker} in {industry}...")
#                     try:
#                         # Create a fresh DB handler for each ticker to ensure clean connections
#                         db_handler = PushFundamentalDataToDB()
#                         db_handler.create_database(dbName)
                        
#                         # Format schema name based on industry
#                         schema_name = industry.lower().replace(' ', '_').replace('&', 'and').replace(',', '_').replace('-', '_')
                        
#                         # Process a single ticker
#                         try:
#                             # Get financial data
#                             financial_data = get_financial_data(ticker, "quarterly", "100")
                            
#                             # Process each financial statement type
#                             if 'financials' in financial_data:
#                                 financials = financial_data['financials']
                                
#                                 # Process income statements
#                                 if 'income_statements' in financials and financials['income_statements']:
#                                     print(f"💰 Uploading income statements for {ticker}...")
#                                     income_df = pd.DataFrame(financials['income_statements'])
#                                     income_df = income_df.replace({pd.NA: None, float('nan'): None})
#                                     income_df['date'] = pd.to_datetime(income_df['calendar_date'])
#                                     db_handler.create_schema_and_table_dynamic(
#                                         dbName, schema_name, f"{ticker}_income_statements", income_df
#                                     )
                                
#                                 # Process balance sheets
#                                 if 'balance_sheets' in financials and financials['balance_sheets']:
#                                     print(f"📑 Uploading balance sheets for {ticker}...")
#                                     balance_df = pd.DataFrame(financials['balance_sheets'])
#                                     balance_df = balance_df.replace({pd.NA: None, float('nan'): None})
#                                     balance_df['date'] = pd.to_datetime(balance_df['calendar_date'])
#                                     db_handler.create_schema_and_table_dynamic(
#                                         dbName, schema_name, f"{ticker}_balance_sheets", balance_df
#                                     )
                                
#                                 # Process cash flow statements
#                                 if 'cash_flow_statements' in financials and financials['cash_flow_statements']:
#                                     print(f"💵 Uploading cash flow statements for {ticker}...")
#                                     cashflow_df = pd.DataFrame(financials['cash_flow_statements'])
#                                     cashflow_df = cashflow_df.replace({pd.NA: None, float('nan'): None})
#                                     cashflow_df['date'] = pd.to_datetime(cashflow_df['calendar_date'])
#                                     db_handler.create_schema_and_table_dynamic(
#                                         dbName, schema_name, f"{ticker}_cash_flow_statements", cashflow_df
#                                     )
                            
#                             # Process financial metrics
#                             if 'financial_metrics' in financial_data and financial_data['financial_metrics']:
#                                 print(f"📊 Uploading financial metrics for {ticker}...")
#                                 metrics_df = pd.DataFrame(financial_data['financial_metrics'])
#                                 metrics_df = metrics_df.replace({pd.NA: None, float('nan'): None})
#                                 metrics_df['date'] = pd.to_datetime(metrics_df['calendar_date'])
#                                 db_handler.create_schema_and_table_dynamic(
#                                     dbName, schema_name, f"{ticker}_financial_metrics", metrics_df
#                                 )
                            
#                             print(f"✅ Completed processing {ticker}")
                            
#                         except Exception as e:
#                             print(f"❌ Error processing {ticker}: {e}")
                            
#                         # Always explicitly close connections
#                         finally:
#                             db_handler.close_connection()
                            
#                         # Pause between API calls to avoid rate limits
#                         print("⏳ Pausing before next company...")
#                         import time
#                         time.sleep(2)
                        
#                     except Exception as outer_e:
#                         print(f"❌ Outer error processing {ticker}: {outer_e}")
#             else:
#                 print(f"❌ Could not find ticker column in sector data for {industry}")
