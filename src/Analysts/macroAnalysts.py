"""
Author: @Michael Laret
=====================================================================
This file contains the functions for the macro analysts.
It is used to get the analyst reports for the different asset classes.
This file has the analysts pull the research reports from the database.
"""

import json
from openai import OpenAI
import numpy as np
import os
import datetime
import psycopg2
import pandas as pd
import re
import time 
from dotenv import load_dotenv
from src.utils.file_utils import load_schema_data

# Load environment variables from .env file
load_dotenv()

OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
client = OpenAI(api_key=OpenAI_API_KEY)
perplexity_model = os.environ.get("PERPLEXITY_MODEL")

# date = datetime.date.today().strftime("%Y_%m_%d")
date = "2025_05_13"

def update_research_date_to_latest():
    """
    Connects to the 'research' database, finds the schema with the most recent date-like name,
    and updates the global 'date' variable to this date.
    Schema names are expected in 'YYYY_MM_DD' format.
    """
    global date
    conn = None
    cur = None
    
    try:
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432)
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"

        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # New approach: Fetch more broadly from SQL, then filter precisely in Python
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT LIKE 'pg_%'    -- Exclude system schemas
              AND schema_name <> 'information_schema'
              AND schema_name <> 'public'
        """)
        potential_schema_names = [row[0] for row in cur.fetchall()]
        
        # Filter for YYYY_MM_DD format using Python's re module
        date_pattern = re.compile(r"^\d{4}_\d{2}_\d{2}$")
        schema_names = [s_name for s_name in potential_schema_names if date_pattern.match(s_name)]
        
        latest_date_str = None
        latest_datetime = None

        for schema_name in schema_names:
            try:
                # Validate and parse the date string
                current_datetime = datetime.datetime.strptime(schema_name, "%Y_%m_%d")
                if latest_datetime is None or current_datetime > latest_datetime:
                    latest_datetime = current_datetime
                    latest_date_str = schema_name
            except ValueError:
                # Schema name is not a valid date in the expected format, ignore it
                print(f"Warning: Schema name '{schema_name}' is not in YYYY_MM_DD format and will be ignored.")
                continue
        
        if latest_date_str:
            date = latest_date_str
            print(f"Research date updated to the latest available: {date}")
        else:
            print("No valid date schemas found in the 'research' database. 'date' variable remains unchanged.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while updating research date: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# Update the date to the latest research date available when the module is loaded
update_research_date_to_latest()

def get_equity_universe():
    """
    Retrieve and format sector/industry/subindustry data from database_schemas.json
    for optimal LLM ingestion.
    
    Returns:
        str: JSON string with hierarchical classification data formatted for LLM
    """
    # Load schema definition
    schema_data = load_schema_data()
    
    # Create nested dictionary structure
    hierarchical_data = {}
    
    # Extract the hierarchical structure
    for sector_name, sector_info in schema_data.items():
        hierarchical_data[sector_name] = {}
        schemas = sector_info.get('schemas', {})
        
        for schema_name, schema_info in schemas.items():
            hierarchical_data[sector_name][schema_name] = []
            tables = schema_info.get('tables', {})
            
            for table_name, table_info in tables.items():
                hierarchical_data[sector_name][schema_name].append(table_name)
    
    # Create context object with metadata
    context = {
        "description": "Financial market hierarchical classification structure",
        "levels": {
            "sector": "Top-level market segment (e.g., 'technology', 'healthcare')",
            "industry": "Sub-segment within a sector",
            "subindustry": "Specific business category within an industry"
        },
        "data": hierarchical_data
    }
    
    # Format with indentation for readability
    return json.dumps(context, indent=2)

def get_etf_universe():
    """
    Retrieve and format ETF classification data from the etf_data database
    for optimal LLM ingestion.
    
    Returns:
        str: JSON string with hierarchical ETF classification data formatted for LLM
    """
    # Database configuration
    db_config = {
        "host": os.getenv('DB_HOST'),
        "user": os.getenv('DB_USER'),
        "password": os.getenv('DB_PASSWORD'),
        "port": os.getenv('DB_PORT'),
        "dbname": os.getenv('DB_NAME')
    }
    
    try:
        # Connect to database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Query to get schema information
        schemas_query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
        ORDER BY schema_name
        """
        cursor.execute(schemas_query)
        schemas = [row[0] for row in cursor.fetchall()]
        
        # Create hierarchical structure
        hierarchical_data = {}
        
        # For each schema, get its tables
        for schema in schemas:
            tables_query = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema}'
            ORDER BY table_name
            """
            cursor.execute(tables_query)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Group tables by category (assuming first part of table name is category)
            categories = {}
            for table in tables:
                parts = table.split('_')
                if len(parts) > 1:
                    category = parts[0]
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(table)
                else:
                    # Handle tables without underscore
                    if 'general' not in categories:
                        categories['general'] = []
                    categories['general'].append(table)
            
            hierarchical_data[schema] = categories
        
        # Create context object with metadata
        context = {
            "description": "ETF classification structure from database",
            "levels": {
                "category": "Top-level ETF category",
                "subcategory": "Specific ETF types within a category",
                "etf": "Individual ETF instruments"
            },
            "data": hierarchical_data
        }
        
        # Format with indentation for readability
        return json.dumps(context, indent=2)
        
    except Exception as e:
        error_msg = f"Error retrieving ETF data: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg})
    
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

def free_search(system_prompt, user_prompt):
    # Define custom analysis steps for equity research
    equity_steps = [
        "Analyzing S&P 500 sector performance",
        "Evaluating market breadth indicators",
        "Processing earnings growth trends",
        "Calculating equity risk premiums",
        "Examining market sentiment metrics",
        "Analyzing technical support/resistance levels",
        "Assessing global equity correlations",
        "Evaluating valuation metrics by sector",
        "Processing institutional fund flows",
        "Analyzing volatility patterns",
        "Calculating sector rotation metrics",
        "Examining factor performance trends",
        "Analyzing earnings surprise data",
        "Evaluating market leadership dynamics",
        "Processing analyst estimate revisions"
    ]
    
    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model='sonar-pro',
            messages=messages,
            stream=True
        )

        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
        for chunk in response:
            collected_chunks.append(chunk)  # Store the raw chunk
            content = chunk.choices[0].delta.content or ""
            collected_content += content  # Concatenate the content
            # Print each new piece as it arrives
            print(content, end="", flush=True)

        # Now collected_content has the full response text
        print("\n\nFull collected response:")

        # Remove the thinking process using regex
        cleaned_content = re.sub(r'<think>.*?</think>', '', collected_content, flags=re.DOTALL)
        
        return cleaned_content
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def commodities_analyst():
    """
    Connects to the 'research' database, queries the commodities_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "commodities_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text

def etf_analyst():
    """
    Connects to the 'research' database, queries the etf_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "etf_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text

def treasuries_analyst():
    """
    Connects to the 'research' database, queries the treasuries table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "treasuries_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text

def foreign_exchange_analyst():
    """
    Connects to the 'research' database, queries the foreign_exchange table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "foreign_exchange_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text

def ig_credit_analyst():
    """
    Connects to the 'research' database, queries the ig_credit_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "ig_credit_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text
   
def high_yield_analyst():
    """
    Connects to the 'research' database, queries the high_yield_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "high_yield_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text

def emerging_market_analyst():
    """
    Connects to the 'research' database, queries the emerging_market_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    conn = None
    cur = None
    research_text = None

    try:
        # Database connection parameters (assuming they are in .env)
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", 5432) # Default PostgreSQL port
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = "research"
        schema_name = date
        table_name = "emerging_market_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print(f"Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
            return None

        # Establish connection
        # Note: psycopg2 is for PostgreSQL. Ensure it's configured correctly for your setup.
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name
        )
        cur = conn.cursor()

        # Construct and execute the SQL query
        # Using %s for parameter substitution to prevent SQL injection
        # Quoting schema and table names
        sql_query = f"""
            SELECT "{text_column_name}" 
            FROM "{schema_name}"."{table_name}" 
            WHERE id = %s;
        """
        cur.execute(sql_query, (target_id,))

        # Fetch the result
        result = cur.fetchone()
        if result:
            research_text = result[0]
        else:
            print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text
