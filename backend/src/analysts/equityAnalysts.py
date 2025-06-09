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
from backend.src.utils.file_utils import load_schema_data
from backend.src.utils.database import get_cursor, execute_query, get_default_db_config, get_single_value
from typing import Optional

# Load environment variables from .env file
load_dotenv()

OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
client = OpenAI(api_key=OpenAI_API_KEY)
perplexity_model = os.environ.get("PERPLEXITY_MODEL")

# Define date as a global variable
date = "2025_01_22"  # Set a default date

def update_research_date_to_latest():
    """
    Update the global date variable to the latest research date found in the database schemas.
    
    Connects to the 'research' database and scans for schemas matching YYYY_MM_DD format,
    then sets the global date variable to the most recent valid date schema found.
    
    Args:
        None
        
    Returns:
        None - Updates the global 'date' variable as a side effect.
    """
    global date
    
    try:
        # Use execute_query to get all schema names
        schema_results = execute_query(
            "research",
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT LIKE 'pg_%'
              AND schema_name <> 'information_schema'
              AND schema_name <> 'public'
            """
        )
        
        if not schema_results:
            print("No schemas found in the 'research' database.")
            return
            
        potential_schema_names = [row[0] for row in schema_results]
        
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

    except Exception as e:
        print(f"An unexpected error occurred while updating research date: {e}")

# Update the date to the latest research date available when the module is loaded
update_research_date_to_latest()

def get_analyst_research(table_name: str) -> Optional[str]:
    """
    Retrieve analyst research content from a specified table in the research database.
    
    Args:
        table_name: Name of the research table to query (e.g., 'energy_research', 'healthcare_research')
        
    Returns:
        str or None: The research text content if found, None if no data exists for the specified table.
    """
    db_name = "research"
    schema_name = date
    target_id = 1
    text_column_name = "content"
    
    # Construct and execute the SQL query
    sql_query = f"""
        SELECT "{text_column_name}" 
        FROM "{schema_name}"."{table_name}" 
        WHERE id = %s
    """
    
    research_text = get_single_value(db_name, sql_query, (target_id,))
    
    if research_text is None:
        print(f"No data found for id {target_id} in table {schema_name}.{table_name}.")
    
    return research_text

def communication_services_analyst():
    """
    Retrieve communication services sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The communication services research content, or None if not found.
    """
    return get_analyst_research("communication_services_research")

def consumer_discretionary_analyst():
    """
    Retrieve consumer discretionary sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The consumer discretionary research content, or None if not found.
    """
    return get_analyst_research("consumer_discretionary_research")

def consumer_staples_analyst():
    """
    Retrieve consumer staples sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The consumer staples research content, or None if not found.
    """
    return get_analyst_research("consumer_staples_research")

def energy_analyst():
    """
    Retrieve energy sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The energy research content, or None if not found.
    """
    return get_analyst_research("energy_research")

def financials_analyst():
    """
    Retrieve financials sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The financials research content, or None if not found.
    """
    return get_analyst_research("financials_research")

def healthcare_analyst():
    """
    Retrieve healthcare sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The healthcare research content, or None if not found.
    """
    return get_analyst_research("healthcare_research")

def industrials_analyst():
    """
    Retrieve industrials sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The industrials research content, or None if not found.
    """
    return get_analyst_research("industrials_research")

def information_technology_analyst():
    """
    Retrieve information technology sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The information technology research content, or None if not found.
    """
    return get_analyst_research("information_technology_research")

def materials_analyst():
    """
    Retrieve materials sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The materials research content, or None if not found.
    """
    return get_analyst_research("materials_research")

def real_estate_analyst():
    """
    Retrieve real estate sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The real estate research content, or None if not found.
    """
    return get_analyst_research("real_estate_research")

def utilities_analyst():
    """
    Retrieve utilities sector research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The utilities research content, or None if not found.
    """
    return get_analyst_research("utilities_research")
    