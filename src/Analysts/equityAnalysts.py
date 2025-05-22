"""
Author: @Michael Laret
=====================================================================
This file contains the functions for the equity analysts.
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
from dotenv import load_dotenv
from src.utils.file_utils import load_schema_data

# Load environment variables from .env file
load_dotenv()

OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
client = OpenAI(api_key=OpenAI_API_KEY)
perplexity_model = os.environ.get("PERPLEXITY_MODEL")


date = "2025_05_11"

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

def communication_services_analyst():
    """
    Connects to the 'research' database, queries the communication_services_research table
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
        table_name = "communication_services_research"
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def consumer_discretionary_analyst():
    """
    Connects to the 'research' database, queries the consumer_discretionary_research table
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
        table_name = "consumer_discretionary_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def consumer_staples_analyst():
    """
    Connects to the 'research' database, queries the consumer_staples_research table
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
        table_name = "consumer_staples_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def energy_analyst():
    """
    Connects to the 'research' database, queries the energy_research table
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
        table_name = "energy_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def financials_analyst():
    """
    Connects to the 'research' database, queries the financials_research table
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
        table_name = "financials_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def healthcare_analyst():
    """
    Connects to the 'research' database, queries the healthcare_research table
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
        table_name = "healthcare_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def industrials_analyst():
    """
    Connects to the 'research' database, queries the industrials_research table
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
        table_name = "industrials_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def information_technology_analyst():
    """
    Connects to the 'research' database, queries the information_technology_research table
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
        table_name = "information_technology_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def materials_analyst():
    """
    Connects to the 'research' database, queries the materials_research table
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
        table_name = "materials_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def real_estate_analyst():
    """
    Connects to the 'research' database, queries the real_estate_research table
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
        table_name = "real_estate_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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

def utilities_analyst():
    """
    Connects to the 'research' database, queries the utilities_research table
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
        table_name = "utilities_research"  # Adjusted table name
        target_id = 1
        text_column_name = "content" # ASSUMPTION: Adjust if your column name is different

        # Check if essential connection parameters are loaded
        if not all([db_host, db_user, db_password]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD) not found in environment variables.")
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
            print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")

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