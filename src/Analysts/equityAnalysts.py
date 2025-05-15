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
import time 
import random
import itertools
import threading
import math
import curses
from dotenv import load_dotenv
from src.portfolio_optimization.phase_one.phaseOneAnimation import start_animation, Colors
from src.utils.file_utils import load_schema_data

# Load environment variables from .env file
load_dotenv()

OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
client = OpenAI(api_key=OpenAI_API_KEY)
perplexity_model = os.environ.get("PERPLEXITY_MODEL")

# Get the current date and format it as YYYY_MM_DD
# date = datetime.date.today().strftime("%Y_%m_%d")
date = "2025_05_13"

def communication_services_analyst():
    """
    Connects to the 'research' database, queries the communication_services_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def consumer_discretionary_analyst():
    """
    Connects to the 'research' database, queries the consumer_discretionary_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def consumer_staples_analyst():
    """
    Connects to the 'research' database, queries the consumer_staples_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def energy_analyst():
    """
    Connects to the 'research' database, queries the energy_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def financials_analyst():
    """
    Connects to the 'research' database, queries the financials_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def healthcare_analyst():
    """
    Connects to the 'research' database, queries the healthcare_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def industrials_analyst():
    """
    Connects to the 'research' database, queries the industrials_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def information_technology_analyst():
    """
    Connects to the 'research' database, queries the information_technology_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def materials_analyst():
    """
    Connects to the 'research' database, queries the materials_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def real_estate_analyst():
    """
    Connects to the 'research' database, queries the real_estate_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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

def utilities_analyst():
    """
    Connects to the 'research' database, queries the utilities_research table
    within the '2025_04_22' schema, and returns the text from the row with id = 1.
    """
    # Import Colors locally for error messages if needed
    from src.portfolio_optimization.phase_one.phaseOneAnimation import Colors 
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