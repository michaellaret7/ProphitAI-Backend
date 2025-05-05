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
import random
import itertools
import threading
import math
import curses
from dotenv import load_dotenv
from src.phaseOne.phaseOneAnimation import start_animation, Colors
from src.utils.file_utils import load_schema_data

# Load environment variables from .env file
load_dotenv()

OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
client = OpenAI(api_key=OpenAI_API_KEY)
perplexity_model = os.environ.get("PERPLEXITY_MODEL")

# date = datetime.date.today().strftime("%Y_%m_%d")
date = "2025_04_29"

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
    from src.phaseOne.phaseOneAnimation import start_animation, Colors

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
    
    # Start animation before API setup
    animation = start_animation(equity_steps, "Communication Services Research")

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

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
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
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def commodities_analyst():
    """
    Connects to the 'research' database, queries the commodities_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
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
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
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
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
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
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
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
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
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
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
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
    # Import Colors locally for error messages if needed
    from src.phaseOne.phaseOneAnimation import Colors 
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
            print(f"{Colors.RED}Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.{Colors.END}")
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
            print(f"{Colors.YELLOW}No data found for id {target_id} in table {schema_name}.{table_name}.{Colors.END}")

    except psycopg2.Error as e:
        print(f"{Colors.RED}Database error: {e}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred: {e}{Colors.END}")
    finally:
        # Ensure cursor and connection are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

    return research_text
