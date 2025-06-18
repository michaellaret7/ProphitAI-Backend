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
from backend.src.utils.file_utils import load_schema_data
from backend.src.utils.database import get_cursor, execute_query, get_default_db_config, get_single_value
from typing import Optional

# Load environment variables from .env file
load_dotenv()

OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
client = OpenAI(api_key=OpenAI_API_KEY)
perplexity_model = os.environ.get("PERPLEXITY_MODEL")

# date = datetime.date.today().strftime("%Y_%m_%d")
date = "2025_05_28"

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
            
        potential_schema_names = [row['schema_name'] for row in schema_results]
        
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

def get_equity_universe():
    """
    Retrieve and format hierarchical equity sector/industry/subindustry classification data.
    
    Loads the equity universe structure from database_schemas.json and formats it into
    a hierarchical JSON structure optimized for LLM consumption with clear metadata.
    
    Args:
        None
        
    Returns:
        str: JSON string containing hierarchical classification data with context metadata.
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
    Retrieve and format ETF classification data from the ETF database.
    
    Queries the etf_data database to extract all schemas and tables, organizing them
    into a hierarchical structure by category for optimal LLM processing.
    
    Args:
        None
        
    Returns:
        str: JSON string with hierarchical ETF classification data or error message if query fails.
    """
    try:
        # Query to get schema information
        schemas_results = execute_query(
            os.getenv('DB_NAME', 'etf_data'),
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
            ORDER BY schema_name
            """
        )
        
        if not schemas_results:
            return json.dumps({"error": "No schemas found in ETF database"})
            
        schemas = [row['schema_name'] for row in schemas_results]
        
        # Create hierarchical structure
        hierarchical_data = {}
        
        # For each schema, get its tables
        for schema in schemas:
            tables_results = execute_query(
                os.getenv('DB_NAME', 'etf_data'),
                f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
                ORDER BY table_name
                """,
                (schema,)
            )
            
            if not tables_results:
                continue
                
            tables = [row['table_name'] for row in tables_results]
            
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

def free_search(system_prompt, user_prompt):
    """
    Execute a free-form search using the Perplexity AI Sonar Pro model.
    
    Sends system and user prompts to the Perplexity API for real-time information retrieval
    and processes the streaming response, cleaning any thinking process tags.
    
    Args:
        system_prompt: The system context/instructions for the AI model.
        user_prompt: The user's query or search request.
        
    Returns:
        str or None: The cleaned response content from the AI model, or None if an error occurs.
    """
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

def get_analyst_research(table_name: str) -> Optional[str]:
    """
    Retrieve analyst research content from a specified table in the research database.
    
    Args:
        table_name: Name of the research table to query (e.g., 'commodities_research', 'etf_research')
        
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
        print(f"Warning: No data found for id {target_id} in table {schema_name}.{table_name}.")
    
    return research_text

def commodities_analyst():
    """
    Retrieve commodities market research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The commodities research content, or None if not found.
    """
    return get_analyst_research("commodities_research")

def etf_analyst():
    """
    Retrieve ETF (Exchange-Traded Fund) research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The ETF research content, or None if not found.
    """
    return get_analyst_research("etf_research")

def treasuries_analyst():
    """
    Retrieve U.S. Treasury securities research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The treasuries research content, or None if not found.
    """
    return get_analyst_research("treasuries_research")

def foreign_exchange_analyst():
    """
    Retrieve foreign exchange (forex) market research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The foreign exchange research content, or None if not found.
    """
    return get_analyst_research("foreign_exchange_research")

def ig_credit_analyst():
    """
    Retrieve investment grade credit market research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The investment grade credit research content, or None if not found.
    """
    return get_analyst_research("ig_credit_research")

def high_yield_analyst():
    """
    Retrieve high yield (junk bond) market research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The high yield research content, or None if not found.
    """
    return get_analyst_research("high_yield_research")

def emerging_market_analyst():
    """
    Retrieve emerging markets research report from the database.
    
    Args:
        None
        
    Returns:
        str or None: The emerging market research content, or None if not found.
    """
    return get_analyst_research("emerging_market_research")

if __name__ == "__main__":
    print(get_etf_universe())
    print(get_equity_universe())