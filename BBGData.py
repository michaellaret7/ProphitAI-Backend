from xbbg import blp
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import psycopg2


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


from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core import SQLDatabase
from llama_index.llms.openai import OpenAI
from sqlalchemy import create_engine, text
import os
# Note: Replace with your OpenAI API key (preferably via environment variables in production)
OpenAI_API_KEY = "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"
os.environ["OPENAI_API_KEY"] = OpenAI_API_KEY
# Get database connection details from the user
print("Please provide your PostgreSQL database connection details:")
host = "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com"
username = "postgres"
password = "ml1710402!"
port = "5432"
db_type = "postgresql"  # Fixed as per your query
database_name = "equity_sector_communication_services"
schema_name = "diversified_telecommunication_services"

# Create the SQLAlchemy engine
connection_string = f"{db_type}://{username}:{password}@{host}:{port}/{database_name}"
engine = create_engine(connection_string)

# Fetch list of tables in the specified schema
with engine.connect() as connection:
    query = text(f"SELECT table_name FROM information_schema.tables WHERE table_schema = :schema_name")
    result = connection.execute(query, {"schema_name": schema_name})
    tables = [row[0] for row in result]

# Check if tables were found
if not tables:
    raise ValueError(f"No tables found in schema '{schema_name}'. Please check the schema name.")

# Define include_tables using table names without schema prefix
include_tables = tables  # e.g., ['alternative_carriers', 'integrated_telecommunication_services']

# Create table descriptions using table names without schema prefix
table_descriptions = {
    table: f"Companies in the {table.replace('_', ' ')} sub-industry"
    for table in tables
}

# Inform the user about the tables included
print("\nTables included in the query engine:")
for table in include_tables:
    print(f"- {schema_name}.{table}: {table_descriptions[table]}")

# Initialize SQLDatabase with schema parameter and custom table info
sql_database = SQLDatabase(
    engine,
    schema=schema_name,           # Specify the schema here
    include_tables=include_tables, # Table names without schema prefix
    custom_table_info=table_descriptions  # Descriptions match table names
)

# Set up the OpenAI LLM
llm = OpenAI(model="gpt-4o", api_key=OpenAI_API_KEY)

# Create the query engine
query_engine = NLSQLTableQueryEngine(sql_database, llm=llm)

# Get the natural language question from the user
question = input("\nEnter your natural language question (e.g., 'What is the average P/E ratio of companies in the alternative carriers sub-industry?'): ")

# Generate and execute the SQL query
response = query_engine.query(question)

# Display the results
print("\nResults:")
print("Question:", question)
print("Generated SQL Query:", response.metadata.get("sql_query", "SQL query not available"))
print("Result:", response.response)