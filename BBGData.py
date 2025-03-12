from xbbg import blp
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import psycopg2
from sqlalchemy import text


def get_fixed_income_data(ticker):
    # Define the ticker and fields
    fields = ["PX_LAST", "YLD_YTM_BID", "YLD_YTM_ASK"]

    # Set end date to current date and calculate start date
    end_date = datetime.now()  # This will use the actual current date
    start_date = end_date - timedelta(days=20*365)

    # Convert dates to strings in the format Bloomberg expects
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Fetch historical data for the last 3 years
    historical_data = blp.bdh(ticker, fields, start_date_str, end_date_str)

    # Display the data
    # print(historical_data)
    return historical_data

# df = pd.read_excel("RatesTickers.xlsx", sheet_name="FI")

# for ticker in df["Tickers"]:
#     # print(df[df["Tickers"] == ticker]["Category"].values[0])
    
#     d = get_fixed_income_data(ticker)
#     if d.empty:
#         print(ticker)

def commodity_data(ticker):
    # Define the ticker and fields for NGA comdty data
    ticker = "NGA Comdty"
    fields = ["PX_LAST", "PX_LOW", "PX_HIGH", "PX_OPEN", "PX_VOLUME"]

    # Set end date to current date and calculate start date for the last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=15*365)

    # Convert dates to strings in the format Bloomberg expects
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Fetch historical NGA comdty data for the last 6 months in 15-minute intervals
    historical_data = blp.bdh(ticker, fields, start_date_str, end_date_str)

    # Display the data
    print(historical_data)


# from llama_index.core.query_engine import NLSQLTableQueryEngine
# from llama_index.core import SQLDatabase
# from llama_index.llms.openai import OpenAI
# from sqlalchemy import create_engine, text
# import os
# # Note: Replace with your OpenAI API key (preferably via environment variables in production)
# OpenAI_API_KEY = "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"
# os.environ["OPENAI_API_KEY"] = OpenAI_API_KEY
# # Get database connection details from the user
# print("Please provide your PostgreSQL database connection details:")
# host = "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com"
# username = "postgres"
# password = "ml1710402!"
# port = "5432"
# db_type = "postgresql"  # Fixed as per your query
# database_name = "equity_sector_communication_services"
# schema_name = "diversified_telecommunication_services"

# # Create the SQLAlchemy engine
# connection_string = f"{db_type}://{username}:{password}@{host}:{port}/{database_name}"
# engine = create_engine(connection_string)

# # Fetch list of tables in the specified schema
# with engine.connect() as connection:
#     query = text(f"SELECT table_name FROM information_schema.tables WHERE table_schema = :schema_name")
#     result = connection.execute(query, {"schema_name": schema_name})
#     tables = [row[0] for row in result]

# # Check if tables were found
# if not tables:
#     raise ValueError(f"No tables found in schema '{schema_name}'. Please check the schema name.")

# # Define include_tables using table names without schema prefix
# include_tables = tables  # e.g., ['alternative_carriers', 'integrated_telecommunication_services']

# # Create table descriptions using table names without schema prefix
# table_descriptions = {
#     table: f"Companies in the {table.replace('_', ' ')} sub-industry"
#     for table in tables
# }

# # Inform the user about the tables included
# print("\nTables included in the query engine:")
# for table in include_tables:
#     print(f"- {schema_name}.{table}: {table_descriptions[table]}")

# # Initialize SQLDatabase with schema parameter and custom table info
# sql_database = SQLDatabase(
#     engine,
#     schema=schema_name,           # Specify the schema here
#     include_tables=include_tables, # Table names without schema prefix
#     custom_table_info=table_descriptions  # Descriptions match table names
# )

# # Set up the OpenAI LLM
# llm = OpenAI(model="gpt-4o", api_key=OpenAI_API_KEY)

# # Create the query engine
# query_engine = NLSQLTableQueryEngine(sql_database, llm=llm)

# # Get the natural language question from the user
# question = input("\nEnter your natural language question (e.g., 'What is the average P/E ratio of companies in the alternative carriers sub-industry?'): ")

# # Generate and execute the SQL query
# response = query_engine.query(question)

# # Display the results
# print("\nResults:")
# print("Question:", question)
# print("Generated SQL Query:", response.metadata.get("sql_query", "SQL query not available"))
# print("Result:", response.response)



def list_database_schemas(db_name):
    """
    Connect to a PostgreSQL database and print all schema names and their tables.
    Excludes system schemas (public, information_schema, pg_catalog).
    Lists ticker symbols under each table.
    
    Args:
        db_name (str): Name of the database to connect to
        db_username (str): PostgreSQL username
        db_password (str): PostgreSQL password
        db_host (str): Database host
        db_port (int): Database port, defaults to 5432
        
    Returns:
        dict: A structured dictionary containing schemas, tables and tickers
    """
    from sqlalchemy import create_engine, text

    db_username = "postgres"
    db_password = "ml1710402!"
    db_host = "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com"
    db_port = 5432  # Use actual numeric port, PostgreSQL default is 5432
        
    # Create connection string and engine
    connection_string = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string)
    
    # Define schemas to exclude
    excluded_schemas = ['public', 'information_schema', 'pg_catalog']
    
    # Query to get schema names (excluding system schemas)
    query = text(f"""
        SELECT schema_name 
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog')
        ORDER BY schema_name
    """)
    
    # Result dictionary
    db_structure = {
        "database": db_name,
        "schemas": {}
    }
    
    # Execute query and fetch results
    with engine.connect() as connection:
        schemas = connection.execute(query).fetchall()
        
        print(f"Schemas and tables in database '{db_name}':")
        
        # For each schema, get its tables
        for schema in schemas:
            schema_name = schema[0]
            
            # Add schema to dictionary
            db_structure["schemas"][schema_name] = {"tables": {}}
            
            # Query to get tables in this schema
            tables_query = text(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema_name
                ORDER BY table_name
            """)
            
            # Get tables for this schema
            tables = connection.execute(tables_query, {"schema_name": schema_name}).fetchall()
            
            print(f"\nSchema: {schema_name}")
            if tables:
                for table in tables:
                    table_name = table[0]
                    print(f"  - Table: {table_name}")
                    
                    # Add table to dictionary
                    db_structure["schemas"][schema_name]["tables"][table_name] = {"tickers": []}
                    
                    try:
                        # First, check if the table has a ticker column
                        columns_query = text(f"""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = :schema_name
                            AND table_name = :table_name
                        """)
                        
                        columns = connection.execute(columns_query, 
                                                    {"schema_name": schema_name, 
                                                     "table_name": table_name}).fetchall()
                        
                        column_names = [col[0].lower() for col in columns]
                        ticker_column = None
                        
                        # Try to find a column that might contain tickers
                        for possible_name in ['ticker', 'symbol', 'ticker_symbol', 'id', 'code']:
                            if possible_name in column_names:
                                ticker_column = possible_name
                                break
                        
                        if ticker_column:
                            # Query to get all tickers from this table
                            tickers_query = text(f"""
                                SELECT DISTINCT "{ticker_column}" 
                                FROM "{schema_name}"."{table_name}"
                                ORDER BY "{ticker_column}"
                            """)
                            
                            tickers = connection.execute(tickers_query).fetchall()
                            if tickers:
                                # Process tickers: remove " US Equity" and filter out empty values
                                processed_tickers = [ticker[0].replace(" US Equity", "") for ticker in tickers if ticker[0]]
                                
                                # Store tickers in dictionary
                                db_structure["schemas"][schema_name]["tables"][table_name]["tickers"] = processed_tickers
                                
                                print(f"    Tickers:")
                                for ticker in processed_tickers:
                                    print(f"      {ticker}")
                            else:
                                print("    No tickers found")
                        else:
                            print("    No ticker column identified")
                    except Exception as e:
                        print(f"    Error retrieving tickers: {str(e)}")
            else:
                print("  (No tables found)")
    
    return db_structure


    
    # Replace with your actual database connection details

db_name = "equity_sector_consumer_staples"

print(list_database_schemas(db_name))