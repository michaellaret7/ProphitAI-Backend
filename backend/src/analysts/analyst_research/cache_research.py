"""
Author: @Michael Laret
=====================================================================
This file is used to store the Perplexity research in the database.
The data from this research is pulled in the phase_one_run.py file.
"""

import psycopg2
import os
from psycopg2 import sql
from datetime import date
from dotenv import load_dotenv
import re
from .equity_research_analysts import *
from .macro_research_analyst import *

# Load environment variables from .env file
load_dotenv()

NEW_DB_NAME = "research"
TABLE_NAME = "communication_services_research"

def setup_research_table_and_insert_data(db_name, table_name, content):
    """
    Connect to database, create schema/table if needed, and insert research content.
    
    Args:
        db_name: Database name to connect to
        table_name: Table name to create/insert into
        content: Research content to insert
    """
    conn = None
    cursor = None
    try:
        # Get connection details from environment variables
        host = os.environ.get("DB_HOST")
        user = os.environ.get("DB_USER")
        password = os.environ.get("DB_PASSWORD")
        port = os.environ.get("DB_PORT")

        if not all([host, user, password, port]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD, DB_PORT) not found in environment variables.")
            return

        # Get current date for schema name
        today_str = date.today().strftime("%Y_%m_%d")
        schema_identifier = sql.Identifier(today_str)
        table_identifier = sql.Identifier(table_name)

        # Connect to the newly created or existing research database
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            dbname=db_name
        )
        cursor = conn.cursor()

        # Create schema if it doesn't exist
        create_schema_query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema_identifier)
        cursor.execute(create_schema_query)
        print(f"Schema '{today_str}' ensured to exist in database '{db_name}'.")

        # Create table if it doesn't exist within the date-based schema
        # Use TEXT data type for potentially large research content
        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.{} (
                id SERIAL PRIMARY KEY,
                content TEXT,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """).format(schema_identifier, table_identifier)
        cursor.execute(create_table_query)
        print(f"Table '{table_name}' ensured to exist in schema '{today_str}'.")

        # --- Clean content before checking duplicates or inserting ---
        cleaned_content = re.sub(r'\[\d+\]', '', content)

        # --- Check for duplicate content before inserting ---
        check_duplicate_query = sql.SQL("""
            SELECT EXISTS (
                SELECT 1
                FROM {}.{}
                WHERE content = %s
                LIMIT 1
            )
        """).format(schema_identifier, table_identifier)

        cursor.execute(check_duplicate_query, (cleaned_content,))
        duplicate_exists = cursor.fetchone()[0]

        if duplicate_exists:
            print(f"Duplicate cleaned content found in '{today_str}.{table_name}'. Skipping insertion.")
        else:
            # Insert the cleaned research data into the schema-qualified table
            insert_query = sql.SQL("INSERT INTO {}.{} (content) VALUES (%s) RETURNING id").format(schema_identifier, table_identifier)
            cursor.execute(insert_query, (cleaned_content,))
            inserted_id = cursor.fetchone()[0] # Get the ID of the inserted row
            conn.commit() # Commit the transaction to save the data
            print(f"Successfully inserted cleaned research text into '{today_str}.{table_name}' with ID: {inserted_id}.")

    except psycopg2.Error as e:
        print(f"Error connecting to '{db_name}', creating table, or inserting data: {e}")
        if conn:
            conn.rollback() # Roll back in case of error during insertion
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"Connection to '{db_name}' closed.")

def run_all_research_analysts():
    """
    Run all equity and macro research analyst functions and store results in database tables.
    
    Returns:
        None: Prints status updates during execution
    """
    db_name = NEW_DB_NAME
    
    # Dictionary mapping analyst functions to their corresponding table names
    analysts = {
        # Equity Research Analysts
        "communication_services_research": communication_services_research_analyst,
        "consumer_discretionary_research": consumer_discretionary_research_analyst,
        "consumer_staples_research": consumer_staples_research_analyst,
        "energy_research": energy_research_analyst,
        "financials_research": financials_research_analyst,
        "healthcare_research": healthcare_research_analyst,
        "industrials_research": industrials_research_analyst,
        "information_technology_research": information_technology_research_analyst,
        "materials_research": materials_research_analyst,
        "real_estate_research": real_estate_research_analyst,
        "utilities_research": utilities_research_analyst,
        
        # Macro Research Analysts
        "commodities_research": commodities_research_analyst,
        "etf_research": etf_research_analyst,
        "treasuries_research": treasuries_research_analyst,
        "foreign_exchange_research": foreign_exchange_research_analyst,
        "ig_credit_research": ig_credit_research_analyst,
        "high_yield_research": high_yield_research_analyst,
        "emerging_market_research": emerging_market_research_analyst
    }
    
    print(f"Starting to run {len(analysts)} research analysts...")
    
    for table_name, analyst_function in analysts.items():
        try:
            print(f"Running {table_name} analyst...")
            research_content = analyst_function()
            
            if research_content:
                print(f"Successfully generated content for {table_name}. Storing in database...")
                setup_research_table_and_insert_data(db_name, table_name, research_content)
            else:
                print(f"No content generated for {table_name}. Skipping database insertion.")
                
        except Exception as e:
            print(f"Error running {table_name} analyst: {e}")
    
    print("Completed running all research analysts.")

if __name__ == "__main__":
    run_all_research_analysts()
