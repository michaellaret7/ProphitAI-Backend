import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
import json
from sqlalchemy import inspect
from typing import Dict, List, Any, Optional, Tuple
import re
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import openai
# Load environment variables
load_dotenv()

# Hard-coded credentials (replace with your actual values)
DB_HOST = "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com"
DB_USER = "postgres"
DB_PASSWORD = "ml1710402!"
DB_PORT = "5432"

# OpenAI API setup - using the hard-coded key if environment variable not available
OpenAI_API_KEY = "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"

client = OpenAI(
    api_key=OpenAI_API_KEY
)

# Global variables
DB_SCHEMA_MAP = {}
DB_SCHEMA_MAP_CACHE_FILE = "db_schema_map.json"
DB_SCHEMA_MAP_CACHE_MAX_AGE_DAYS = 7

# Keyword maps for query parsing
sector_map = {}
industry_map = {}
sub_industry_map = {}

# Initialize global variables
DB_SCHEMA_MAP = {}
SECTOR_KEYWORDS = {}
INDUSTRY_KEYWORDS = {}
SUBINDUSTRY_KEYWORDS = {}

# Database connections - configure with your actual connection strings
db_connections = {
    "postgres": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres", 
    "equity_sector_communication_services": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_communication_services",
    "equity_sector_consumer_discretionary": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_consumer_discretionary",
    "equity_sector_consumer_staples": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_consumer_staples",
    "equity_sector_energy": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_energy",
    "equity_sector_financials": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_financials",
    "equity_sector_health_care": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_health_care",
    "equity_sector_industrials": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_industrials",
    "equity_sector_information_technology": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_information_technology",
    "equity_sector_materials": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_materials",
    "equity_sector_real_estate": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_real_estate",
    "equity_sector_utilities": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_utilities",
    "commodity_data": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/commodity_data",
    "etf_data": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/etf_data",
    "equity_sector_communication_services_prices": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_communication_services_prices",
    "equity_sector_consumer_discretionary_prices": f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/equity_sector_consumer_discretionary_prices",
    # Add other price and fundamentals databases similarly
}

# Database descriptions for routing
descriptions = {
    "equity_sector_communication_services": "Information about companies in the communication services sector",
    "equity_sector_consumer_discretionary": "Information about companies in the consumer discretionary sector",
    "equity_sector_consumer_staples": "Information about companies in the consumer staples sector",
    "equity_sector_energy": "Information about companies in the energy sector",
    "equity_sector_financials": "Information about companies in the financials sector",
    "equity_sector_health_care": "Information about companies in the health care sector",
    "equity_sector_industrials": "Information about companies in the industrials sector",
    "equity_sector_information_technology": "Information about companies in the information technology sector",
    "equity_sector_materials": "Information about companies in the materials sector",
    "equity_sector_real_estate": "Information about companies in the real estate sector",
    "equity_sector_utilities": "Information about companies in the utilities sector",
    "commodity_data": "Information about commodity prices and data",
    "etf_data": "Information about ETFs and their performance",
    "equity_sector_communication_services_prices": "Stock price data for communication services companies",
    "equity_sector_consumer_discretionary_prices": "Stock price data for consumer discretionary companies",
    # Add other price and fundamentals databases similarly
}

def get_db_connection(dbname="postgres"):
    """Establish a connection to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            dbname=dbname
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database {dbname}: {e}")
        return None

def get_stocks_by_sector(sector):
    """Query stocks from a specific sector (database)
    
    Args:
        sector (str): Sector name like "equity_sector_energy"
    
    Returns:
        DataFrame: All stocks in the sector
    """
    conn = get_db_connection(sector)
    if not conn:
        return pd.DataFrame()
    
    try:
        cursor = conn.cursor()
        
        # Get all schemas that aren't system schemas
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'public')
        """)
        
        schemas = [schema[0] for schema in cursor.fetchall()]
        all_stocks = []
        
        # For each schema (industry), get all tables (subindustries)
        for schema in schemas:
            cursor.execute(f"""
                SELECT table_name 
                FROM information_schema.tables
                WHERE table_schema = '{schema}'
                AND table_type = 'BASE TABLE'
            """)
            
            tables = [table[0] for table in cursor.fetchall()]
            
            # For each table, get all stocks
            for table in tables:
                try:
                    cursor.execute(f"""
                        SELECT * FROM "{schema}"."{table}"
                    """)
                    
                    columns = [desc[0] for desc in cursor.description]
                    for row in cursor.fetchall():
                        stock_data = dict(zip(columns, row))
                        # Add metadata if not already in the data
                        if 'sector' not in stock_data:
                            stock_data['sector'] = sector.replace('equity_sector_', '')
                        if 'industry' not in stock_data:
                            stock_data['industry'] = schema
                        if 'sub_industry' not in stock_data:
                            stock_data['sub_industry'] = table
                        all_stocks.append(stock_data)
                except Exception as e:
                    print(f"Error querying table '{table}' in schema '{schema}': {e}")
                    continue
        
        return pd.DataFrame(all_stocks)
    except Exception as e:
        print(f"Error querying sector {sector}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_stocks_by_industry(sector, industry):
    """Query stocks from a specific industry (schema)
    
    Args:
        sector (str): Sector name like "equity_sector_energy"
        industry (str): Industry name like "oil__gas_and_consumable_fuels"
    
    Returns:
        DataFrame: All stocks in the industry
    """
    conn = get_db_connection(sector)
    if not conn:
        return pd.DataFrame()
    
    try:
        cursor = conn.cursor()
        
        # Get all tables in the industry schema
        cursor.execute(f"""
            SELECT table_name 
            FROM information_schema.tables
            WHERE table_schema = '{industry}'
            AND table_type = 'BASE TABLE'
        """)
        
        tables = [table[0] for table in cursor.fetchall()]
        all_stocks = []
        
        # For each table (subindustry), get all stocks
        for table in tables:
            try:
                cursor.execute(f"""
                    SELECT * FROM "{industry}"."{table}"
                """)
                
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    stock_data = dict(zip(columns, row))
                    # Add metadata if not already in the data
                    if 'sector' not in stock_data:
                        stock_data['sector'] = sector.replace('equity_sector_', '')
                    if 'industry' not in stock_data:
                        stock_data['industry'] = industry
                    if 'sub_industry' not in stock_data:
                        stock_data['sub_industry'] = table
                    all_stocks.append(stock_data)
            except Exception as e:
                print(f"Error querying table '{table}' in schema '{industry}': {e}")
                continue
        
        return pd.DataFrame(all_stocks)
    except Exception as e:
        print(f"Error querying industry {industry} in sector {sector}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_stocks_by_subindustry(sector, industry, subindustry):
    """Query stocks from a specific subindustry (table)
    
    Args:
        sector (str): Sector name like "equity_sector_energy"
        industry (str): Industry name like "oil__gas_and_consumable_fuels"
        subindustry (str): Subindustry name like "integrated_oil_and_gas"
    
    Returns:
        DataFrame: All stocks in the subindustry
    """
    conn = get_db_connection(sector)
    if not conn:
        return pd.DataFrame()
    
    try:
        cursor = conn.cursor()
        
        # Query the specific table
        cursor.execute(f"""
            SELECT * FROM "{industry}"."{subindustry}"
        """)
        
        columns = [desc[0] for desc in cursor.description]
        all_stocks = []
        
        for row in cursor.fetchall():
            stock_data = dict(zip(columns, row))
            # Add metadata if not already in the data
            if 'sector' not in stock_data:
                stock_data['sector'] = sector.replace('equity_sector_', '')
            if 'industry' not in stock_data:
                stock_data['industry'] = industry
            if 'sub_industry' not in stock_data:
                stock_data['sub_industry'] = subindustry
            all_stocks.append(stock_data)
        
        return pd.DataFrame(all_stocks)
    except Exception as e:
        print(f"Error querying subindustry {subindustry} in industry {industry}, sector {sector}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# Note: If this fails, install the OpenAI llama_index package with:
# pip install llama-index-llms-openai
from llama_index.core.query_engine import NLSQLTableQueryEngine, RouterQueryEngine
from llama_index.core import SQLDatabase
from openai import OpenAI  # Using openai directly instead of llama_index wrapper
from sqlalchemy import create_engine

def build_database_schema_map(force_rebuild=False):
    """
    Build a map of database schemas and tables.
    
    Args:
        force_rebuild (bool): If True, rebuilds the cache even if a recent one exists
        
    Returns:
        Dict: Database schema map
    """
    global DB_SCHEMA_MAP
    
    # Check for existing cache file
    cache_path = Path(DB_SCHEMA_MAP_CACHE_FILE)
    
    if not force_rebuild and cache_path.exists():
        # Check if cache file is recent enough
        cache_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        cache_age = datetime.now() - cache_mtime
        
        if cache_age < timedelta(days=DB_SCHEMA_MAP_CACHE_MAX_AGE_DAYS):
            try:
                print(f"Loading database schema map from cache ({cache_age.days} days old)...")
                with open(cache_path, 'r') as f:
                    DB_SCHEMA_MAP = json.load(f)
                print(f"Successfully loaded schema map from cache with {len(DB_SCHEMA_MAP)} databases")
                return DB_SCHEMA_MAP
            except Exception as e:
                print(f"Error loading cache: {str(e)}. Building new schema map...")
    
    # If we reach here, we need to build the schema map
    DB_SCHEMA_MAP = {}
    
    schema_map = {}
    
    # Loop through each database (sector)
    for db_name, conn_str in db_connections.items():
        try:
            print(f"Mapping database: {db_name}")
            # Create engine for this database
            engine = create_engine(conn_str)
            inspector = inspect(engine)
            
            # Get all schemas
            schemas = inspector.get_schema_names()
            schemas = [schema for schema in schemas if schema not in ('information_schema', 'pg_catalog')]
            
            db_info = {
                "description": descriptions.get(db_name, f"Database for {db_name}"),
                "schemas": {}
            }
            
            # For each schema (industry)
            for schema in schemas:
                schema_info = {
                    "tables": {}
                }
                
                # Get all tables in this schema
                tables = inspector.get_table_names(schema=schema)
                
                # For each table (subindustry)
                for table in tables:
                    # Get columns in this table
                    try:
                        columns = inspector.get_columns(table, schema=schema)
                        column_info = {col['name']: {
                            "type": str(col['type']),
                            "nullable": col.get('nullable', True)
                        } for col in columns}
                        
                        schema_info["tables"][table] = {
                            "columns": column_info
                        }
                    except Exception as e:
                        print(f"Error getting columns for {schema}.{table}: {str(e)}")
                
                db_info["schemas"][schema] = schema_info
            
            schema_map[db_name] = db_info
            
        except Exception as e:
            print(f"Error mapping database {db_name}: {str(e)}")
    
    # Store the map globally
    DB_SCHEMA_MAP = schema_map
    
    # After building the map, save it to cache
    try:
        with open(cache_path, 'w') as f:
            json.dump(DB_SCHEMA_MAP, f, indent=2)
        print(f"Saved database schema map to cache at {cache_path}")
    except Exception as e:
        print(f"Warning: Failed to save schema map to cache: {str(e)}")
    
    return DB_SCHEMA_MAP

def build_keyword_maps():
    """
    Build mappings from natural language keywords to database objects
    
    Returns:
        Tuple[Dict, Dict, Dict]: (sector_map, industry_map, sub_industry_map)
    """
    global SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS, DB_SCHEMA_MAP
    
    print("Loading keyword maps from schema...")
    
    # Start with hard-coded mappings for critical paths
    SECTOR_KEYWORDS = {
        "technology": "equity_sector_information_technology",
        "tech": "equity_sector_information_technology",
        "it": "equity_sector_information_technology",
        "software": "equity_sector_information_technology",
        "tech companies": "equity_sector_information_technology",
        
        "automobile": "equity_sector_consumer_discretionary",
        "auto": "equity_sector_consumer_discretionary",
        "car": "equity_sector_consumer_discretionary",
        "cars": "equity_sector_consumer_discretionary",
        
        "energy": "equity_sector_energy",
        "oil": "equity_sector_energy",
        "gas": "equity_sector_energy",
        
        "healthcare": "equity_sector_health_care",
        "health care": "equity_sector_health_care",
        "health": "equity_sector_health_care",
        "medical": "equity_sector_health_care",
        "pharma": "equity_sector_health_care",
        "pharmaceutical": "equity_sector_health_care",
        "biotech": "equity_sector_health_care",
        
        "financial": "equity_sector_financials",
        "finance": "equity_sector_financials",
        "banks": "equity_sector_financials",
        "banking": "equity_sector_financials",
        
        "consumer": "equity_sector_consumer_discretionary",
        "retail": "equity_sector_consumer_discretionary",
        
        "industrial": "equity_sector_industrials",
        "industrials": "equity_sector_industrials",
        "manufacturing": "equity_sector_industrials",
        
        "materials": "equity_sector_materials",
        "chemicals": "equity_sector_materials",
        
        "utilities": "equity_sector_utilities",
        "utility": "equity_sector_utilities",
        
        "telecom": "equity_sector_communication_services",
        "communication": "equity_sector_communication_services",
        "communications": "equity_sector_communication_services",
        "media": "equity_sector_communication_services",
        
        "real estate": "equity_sector_real_estate",
        "reits": "equity_sector_real_estate",
        "property": "equity_sector_real_estate"
    }
    
    INDUSTRY_KEYWORDS = {
        "automobile": "automobiles",
        "auto parts": "automobile_components",
        "auto components": "automobile_components",
        "software": "software",
        "semiconductor": "semiconductors_and_semiconductor_equipment",
        "oil": "oil__gas_and_consumable_fuels",
        "gas": "oil__gas_and_consumable_fuels",
        "energy": "oil__gas_and_consumable_fuels",
        "healthcare equipment": "health_care_equipment_and_supplies",
        "medical devices": "health_care_equipment_and_supplies",
        "biotech": "biotechnology",
        "pharmaceutical": "pharmaceuticals",
        "pharma": "pharmaceuticals",
        "health providers": "health_care_providers_and_services",
        "hospitals": "health_care_providers_and_services"
    }
    
    SUBINDUSTRY_KEYWORDS = {
        "auto manufacturers": "automobile_manufacturers",
        "auto parts": "automotive_parts_and_equipment",
        "semiconductors": "semiconductors",
        "application software": "application_software",
        "system software": "systems_software",
        "oil and gas": "oil_and_gas_exploration_and_production",
        "integrated oil": "integrated_oil_and_gas",
        "medical equipment": "health_care_equipment",
        "medical supplies": "health_care_supplies",
        "biotech": "biotechnology",
        "pharma": "pharmaceuticals"
    }
    
    # Only proceed with schema-based mapping if DB_SCHEMA_MAP exists
    if not DB_SCHEMA_MAP:
        print("Warning: DB_SCHEMA_MAP is empty, using only hard-coded keyword maps")
        return (SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS)
    
    try:
        # Add mappings based on database schema
        for db_name, db_info in DB_SCHEMA_MAP.items():
            # Extract sector from database name
            if db_name.startswith("equity_sector_"):
                sector = db_name.replace("equity_sector_", "").replace("_", " ")
                SECTOR_KEYWORDS[sector] = db_name
                
            # Extract industries and sub-industries from schemas and tables
            if "schemas" in db_info:
                for schema_name, schema_info in db_info["schemas"].items():
                    # Clean up schema name for display
                    display_schema = schema_name.replace("_", " ")
                    INDUSTRY_KEYWORDS[display_schema] = schema_name
                    
                    # Handle tables (sub-industries)
                    if "tables" in schema_info:
                        for table_name in schema_info["tables"]:
                            display_table = table_name.replace("_", " ")
                            SUBINDUSTRY_KEYWORDS[display_table] = table_name
                            
                            # Also add specific combinations
                            combined = f"{display_schema} {display_table}"
                            SUBINDUSTRY_KEYWORDS[combined] = table_name
                            
    except Exception as e:
        print(f"Error building keyword maps from schema: {str(e)}")
        print("Continuing with hard-coded mappings")
    
    return (SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS)

def get_db_table_for_query(query: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Determine the most relevant database, schema, and table for a natural language query.
    
    Args:
        query (str): Natural language query
        
    Returns:
        Tuple[str, Optional[str], Optional[str]]: (database_name, schema_name, table_name)
    """
    global SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS, DB_SCHEMA_MAP
    
    # Ensure schema map is built
    if not DB_SCHEMA_MAP:
        print("Loading database schema map...")
        build_database_schema_map(force_rebuild=False)
    
    # Ensure keyword maps are built
    if not SECTOR_KEYWORDS or not INDUSTRY_KEYWORDS or not SUBINDUSTRY_KEYWORDS:
        print("Building keyword maps...")
        SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS = build_keyword_maps()
    
    query_lower = query.lower()
    
    # Special case for automobile industry
    if "automobile" in query_lower or "automotive" in query_lower or "car industry" in query_lower:
        if "parts" in query_lower or "component" in query_lower:
            return "equity_sector_consumer_discretionary", "automobile_components", "automotive_parts_and_equipment"
        else:
            return "equity_sector_consumer_discretionary", "automobiles", "automobile_manufacturers"
    
    # Find best subindustry match first (most specific)
    best_subindustry = find_matching_phrase(query_lower, SUBINDUSTRY_KEYWORDS.keys())
    if best_subindustry:
        print(f"Keyword match to subindustry: {best_subindustry}")
        table = SUBINDUSTRY_KEYWORDS[best_subindustry]
        # Find the schema containing this table
        for db_name, db_info in DB_SCHEMA_MAP.items():
            if "schemas" in db_info:
                for schema_name, schema_info in db_info["schemas"].items():
                    if "tables" in schema_info and table in schema_info["tables"]:
                        return db_name, schema_name, table
    
    # Find best industry match next
    best_industry = find_matching_phrase(query_lower, INDUSTRY_KEYWORDS.keys())
    if best_industry:
        print(f"Keyword match to industry: {best_industry}")
        schema = INDUSTRY_KEYWORDS[best_industry]
        # Find the DB containing this schema
        for db_name, db_info in DB_SCHEMA_MAP.items():
            if "schemas" in db_info and schema in db_info["schemas"]:
                return db_name, schema, None
    
    # Find sector match last (most general)
    best_sector = find_matching_phrase(query_lower, SECTOR_KEYWORDS.keys())
    if best_sector:
        print(f"Keyword match to sector: {best_sector}")
        return SECTOR_KEYWORDS[best_sector], None, None
    
    # Default to consumer discretionary if no match
    print("No keyword match found, using default")
    return "equity_sector_consumer_discretionary", None, None

def explore_database_schema(dbname=None):
    """
    Print out the database schema in a human-readable format
    
    Args:
        dbname (str, optional): Specific database to explore. If None, explore all.
    """
    # Build schema map if not already built
    if not DB_SCHEMA_MAP:
        build_database_schema_map()
    
    if dbname and dbname in DB_SCHEMA_MAP:
        # Print just the specified database
        db_info = DB_SCHEMA_MAP[dbname]
        print(f"\n=== DATABASE: {dbname} ===")
        print(f"Description: {db_info['description']}")
        print(f"Schemas: {len(db_info['schemas'])}")
        
        for schema_name, schema_info in db_info['schemas'].items():
            print(f"\n  ## SCHEMA: {schema_name} ##")
            
            for table_name, table_info in schema_info['tables'].items():
                print(f"    TABLE: {table_name}")
                print(f"      COLUMNS: {', '.join(table_info['columns'].keys())}")
    else:
        # Print summary of all databases
        print("\n=== DATABASE SUMMARY ===")
        for db_name, db_info in DB_SCHEMA_MAP.items():
            schema_count = len(db_info['schemas'])
            table_count = sum(len(schema_info['tables']) for schema_info in db_info['schemas'].values())
            print(f"{db_name}: {schema_count} schemas, {table_count} tables")

def extract_query_conditions(natural_language_query):
    """
    Extract common filtering conditions from a natural language query.
    
    Args:
        natural_language_query (str): Natural language query
        
    Returns:
        dict: Dictionary of conditions extracted from the query
    """
    query_lower = natural_language_query.lower()
    conditions = {}
    
    # Print the query for debugging
    print(f"Extracting conditions from: '{query_lower}'")
    
    # General pattern for 'greater than' conditions
    gt_pattern = r'(alpha|p[ /]e|price[ -]to[ -]earnings|market\s+cap|dividend\s+yield|roe|return\s+on\s+equity|beta|profit\s+margin|debt\s+to\s+equity|leverage|ebitda|revenue|fcf|free\s+cash\s+flow|eps|earnings\s+per\s+share)\s+(?:of\s+)?(?:over|above|greater than|>)\s+(?:over|above|greater than|>)?\s*([\d.]+)(?:%|\s*percent|k|m|b|bn|million|billion|trillion)?'
    
    # General pattern for 'less than' conditions
    lt_pattern = r'(alpha|p[ /]e|price[ -]to[ -]earnings|market\s+cap|dividend\s+yield|roe|return\s+on\s+equity|beta|profit\s+margin|debt\s+to\s+equity|leverage|ebitda|revenue|fcf|free\s+cash\s+flow|eps|earnings\s+per\s+share)\s+(?:of\s+)?(?:less than|under|below|<)\s+(?:less than|under|below|<)?\s*([\d.]+)(?:%|\s*percent|k|m|b|bn|million|billion|trillion)?'
    
    # Additional pattern for 'with less than X beta' format
    with_lt_pattern = r'with\s+(?:less than|under|below|<)\s+(?:less than|under|below|<)?\s*([\d.]+)\s+(alpha|p[ /]e|price[ -]to[ -]earnings|market\s+cap|dividend\s+yield|roe|return\s+on\s+equity|beta|profit\s+margin|debt\s+to\s+equity|leverage|ebitda|revenue|fcf|free\s+cash\s+flow|eps|earnings\s+per\s+share)'
    
    # Additional pattern for 'with beta less than X' format
    with_metric_lt_pattern = r'with\s+(alpha|p[ /]e|price[ -]to[ -]earnings|market\s+cap|dividend\s+yield|roe|return\s+on\s+equity|beta|profit\s+margin|debt\s+to\s+equity|leverage|ebitda|revenue|fcf|free\s+cash\s+flow|eps|earnings\s+per\s+share)\s+(?:less than|under|below|<)\s+(?:less than|under|below|<)?\s*([\d.]+)'
    
    # Map of natural language metric names to database column names
    metric_map = {
        "alpha": "alpha_m_3",
        "p/e": "p_e", 
        "pe": "p_e",
        "price to earnings": "p_e",
        "market cap": "market_cap",
        "dividend yield": "dividend_yield",
        "roe": "roe",
        "return on equity": "roe",
        "beta": "beta_m_3",
        "profit margin": "profit_margin",
        "debt to equity": "net_debt_to_ebitda_lf",
        "leverage": "net_debt_to_ebitda_lf",
        "ebitda": "ebitda_t12m",
        "revenue": "revenue",
        "fcf": "fcf",
        "free cash flow": "fcf",
        "eps": "eps",
        "earnings per share": "eps"
    }
    
    # Process greater than conditions
    for match in re.finditer(gt_pattern, query_lower):
        metric_name = match.group(1).strip()
        value_str = match.group(2).strip()
        value = float(value_str)
        
        # Check for unit multipliers
        if match.group(0).find('percent') > -1 or match.group(0).find('%') > -1:
            # Convert percentage to decimal for financial ratios
            if metric_name in ["dividend yield", "roe", "return on equity", "profit margin"]:
                value = value / 100
        elif match.group(0).find('million') > -1 or match.group(0).find('m') > -1:
            value = value * 1000000
        elif match.group(0).find('billion') > -1 or match.group(0).find('b') > -1 or match.group(0).find('bn') > -1:
            value = value * 1000000000
        elif match.group(0).find('trillion') > -1:
            value = value * 1000000000000
        elif match.group(0).find('k') > -1:
            value = value * 1000
        
        # Map to the actual column name
        for key, column in metric_map.items():
            if key in metric_name:
                conditions[key.replace(' ', '_')] = {
                    'column': column,
                    'operator': '>',
                    'value': value
                }
                print(f"Found GT condition: {key} > {value}")
                break
    
    # Process less than conditions
    for match in re.finditer(lt_pattern, query_lower):
        metric_name = match.group(1).strip()
        value_str = match.group(2).strip()
        value = float(value_str)
        
        # Check for unit multipliers (same as above)
        if match.group(0).find('percent') > -1 or match.group(0).find('%') > -1:
            if metric_name in ["dividend yield", "roe", "return on equity", "profit margin"]:
                value = value / 100
        elif match.group(0).find('million') > -1 or match.group(0).find('m') > -1:
            value = value * 1000000
        elif match.group(0).find('billion') > -1 or match.group(0).find('b') > -1 or match.group(0).find('bn') > -1:
            value = value * 1000000000
        elif match.group(0).find('trillion') > -1:
            value = value * 1000000000000
        elif match.group(0).find('k') > -1:
            value = value * 1000
        
        # Map to the actual column name
        for key, column in metric_map.items():
            if key in metric_name:
                conditions[key.replace(' ', '_')] = {
                    'column': column,
                    'operator': '<',
                    'value': value
                }
                print(f"Found LT condition: {key} < {value}")
                break
    
    # Process 'with less than X beta' format
    for match in re.finditer(with_lt_pattern, query_lower):
        value_str = match.group(1).strip()
        metric_name = match.group(2).strip()
        value = float(value_str)
        
        # Apply unit multipliers if present
        full_match = match.group(0)
        if 'percent' in full_match or '%' in full_match:
            if metric_name in ["dividend yield", "roe", "return on equity", "profit margin"]:
                value = value / 100
        
        # Map to the actual column name
        for key, column in metric_map.items():
            if key in metric_name:
                conditions[key.replace(' ', '_')] = {
                    'column': column,
                    'operator': '<',
                    'value': value
                }
                print(f"Found WITH-LT condition: {key} < {value}")
                break
    
    # Process 'with beta less than X' format
    for match in re.finditer(with_metric_lt_pattern, query_lower):
        metric_name = match.group(1).strip()
        value_str = match.group(2).strip()
        value = float(value_str)
        
        # Apply unit multipliers if present
        full_match = match.group(0)
        if 'percent' in full_match or '%' in full_match:
            if metric_name in ["dividend yield", "roe", "return on equity", "profit margin"]:
                value = value / 100
        
        # Map to the actual column name
        for key, column in metric_map.items():
            if key in metric_name:
                conditions[key.replace(' ', '_')] = {
                    'column': column,
                    'operator': '<',
                    'value': value
                }
                print(f"Found WITH-METRIC-LT condition: {key} < {value}")
                break
    
    return conditions

def generate_sql_query(natural_language_query):
    """
    Generate a SQL query from a natural language query using OpenAI API.
    
    Args:
        natural_language_query (str): Natural language query
        
    Returns:
        str: Generated SQL query
    """
    global DB_SCHEMA_MAP, SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS
    
    # Ensure schema map is built
    if not DB_SCHEMA_MAP:
        print("Loading database schema map for SQL generation...")
        build_database_schema_map(force_rebuild=False)
    
    # Ensure keyword maps are built
    if not SECTOR_KEYWORDS or not INDUSTRY_KEYWORDS or not SUBINDUSTRY_KEYWORDS:
        print("Building keyword maps for SQL generation...")
        SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS = build_keyword_maps()
    
    # Extract common conditions from the query
    conditions = extract_query_conditions(natural_language_query)
    
    # Print extracted conditions for debugging
    if conditions:
        print("SQL Generation - Extracted conditions:")
        for cond_type, cond_info in conditions.items():
            print(f"  - {cond_type}: {cond_info['column']} {cond_info['operator']} {cond_info['value']}")
    else:
        print("SQL Generation - No conditions were extracted from the query")
    
    # Build WHERE clause
    where_conditions = []
    for cond_type, cond_info in conditions.items():
        where_conditions.append(f"{cond_info['column']} {cond_info['operator']} {cond_info['value']}")
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
        print(f"SQL Generation - Using WHERE clause: {where_clause}")
    
    # Determine database and target tables
    db_name, schema_name, table_name = get_db_table_for_query(natural_language_query)
    print(f"Determined query targets: DB={db_name}, Schema={schema_name}, Table={table_name}")
    
    # Build context based on the database and schema
    context = "Database structure information:\n"
    
    # Extract limit information for the prompt
    extracted_limit = extract_limit_from_query(natural_language_query)
    limit_info = ""
    if extracted_limit == -1:
        limit_info = "NOTE: User has requested ALL results (do not apply LIMIT unless sorting is used, then use a large limit like 1000)"
    elif extracted_limit is not None:
        limit_info = f"NOTE: User has requested a limit of {extracted_limit} results"
    else:
        limit_info = "NOTE: No specific limit requested, default to LIMIT 5"
    
    # Build context for the query - helps the LLM understand the database structure
    context += f"Database: {db_name}\n"
    
    # Add extracted conditions to the context so LLM can use them
    if where_clause:
        context += f"\n{where_clause}\n"
    
    # Add suggestions for how to handle these conditions in SQL
    if conditions:
        context += "Suggested SQL snippets for these conditions:\n"
        for cond_type, cond_info in conditions.items():
            context += f"- WHERE {cond_info['column']} {cond_info['operator']} {cond_info['value']}\n"
        
        # Suggest a complete WHERE clause
        if where_conditions:
            context += f"\nComplete WHERE clause: WHERE {' AND '.join(where_conditions)}\n"
    
    # Add information about what columns should be included
    if conditions:
        columns = ["ticker", "short_name", "industry"]
        for cond_type, cond_info in conditions.items():
            col = cond_info['column']
            if col not in columns:
                columns.append(col)
        
        context += f"\nSuggested columns to include: {', '.join(columns)}\n"
    
    # Create system prompt
    system_prompt = f"""You are an SQL expert. Generate a PostgreSQL query for the following question:
    
{natural_language_query}

{limit_info}

The query should be run against this database structure:
{context}

Important guidelines:
1. For sorting, use ORDER BY clause. For filtering, use WHERE clause.
2. When the user asks for ALL results, do not use a LIMIT clause unless sorting is needed, then use LIMIT 1000.
3. When querying across multiple tables, use UNION ALL to combine results.
4. Ensure column references in WHERE, ORDER BY, etc. are consistent across all UNION'ed queries.
5. ALWAYS use full schema.table notation for table references (like 'automobiles.automobile_manufacturers').
6. If dealing with lowest/highest values, use ORDER BY with ASC/DESC and LIMIT.
7. NEVER use placeholder names like 'schema_name.table_name' - always use the ACTUAL schema and table names.
8. ALWAYS assume these common columns exist: ticker, short_name, industry, p_e, market_cap

Generate ONLY the SQL query, with no explanations or comments."""

    # Call OpenAI API
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": natural_language_query}
            ],
            temperature=0
        )
        
        # Clean the SQL query - remove markdown code blocks if present
        sql_query = response.choices[0].message.content.strip()
        sql_query = re.sub(r'^```\s*sql\s*', '', sql_query)
        sql_query = re.sub(r'```$', '', sql_query)
        sql_query = sql_query.strip()
        
        # Remove trailing semicolons
        sql_query = sql_query.rstrip(';')
        
        print(f"Generated SQL query: {sql_query}")
        return sql_query
        
    except Exception as e:
        print(f"Error generating SQL query: {e}")
        
        # Fallback for common query types
        limit = extracted_limit if extracted_limit else 5
        if "automobile" in natural_language_query.lower():
            if "parts" in natural_language_query.lower():
                return f"""
                SELECT ticker, short_name, industry 
                FROM automobile_components.automotive_parts_and_equipment
                LIMIT {limit}
                """
            else:
                return f"""
                SELECT ticker, short_name, industry, p_e, market_cap 
                FROM automobiles.automobile_manufacturers
                ORDER BY market_cap DESC
                LIMIT {limit}
                """
        
        if "energy" in natural_language_query.lower():
            return f"""
            SELECT ticker, short_name, industry, p_e
            FROM oil__gas_and_consumable_fuels.integrated_oil_and_gas
            LIMIT {limit}
            """
        
        raise Exception(f"Failed to generate SQL query: {str(e)}")

def execute_sql_query(sql_query, dbname=None):
    """
    Execute a SQL query on the specified database.
    
    Args:
        sql_query (str): SQL query to execute
        dbname (str, optional): Database name. Defaults to None.
        
    Returns:
        pandas.DataFrame: Results of the query
    """
    # If no database specified, use postgres
    if not dbname:
        dbname = "postgres"
    
    # Ensure the database name is in our configured connections
    if dbname not in db_connections:
        print(f"Error: Database '{dbname}' not in configured connections")
        return pd.DataFrame()
    
    connection_string = db_connections[dbname]
    
    try:
        # Create a SQLAlchemy engine
        engine = create_engine(connection_string)
        
        # Print the SQL query for debugging
        print("Executing SQL query:", sql_query)
        
        # Execute query and return results as a pandas DataFrame
        df = pd.read_sql_query(sql_query, engine)
        
        # Print rows found
        print(f"Query returned {len(df)} rows")
        return df
        
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        
        # More informative error messages
        if "UndefinedTable" in str(e):
            # Extract table name for more helpful message
            match = re.search(r'relation "([^"]+)" does not exist', str(e))
            if match:
                bad_relation = match.group(1)
                print(f"Bad relation: {bad_relation}")
                
                # Try to suggest a possible alternative
                if '.' in bad_relation:
                    schema, table = bad_relation.split('.')
                    if schema in DB_SCHEMA_MAP.get(dbname, {}).get("schemas", {}):
                        tables = list(DB_SCHEMA_MAP[dbname]["schemas"][schema]["tables"].keys())
                        if tables:
                            print(f"Available tables in {schema}: {', '.join(tables[:5])}" + 
                                  (", ..." if len(tables) > 5 else ""))
        
        elif "UndefinedColumn" in str(e):
            # Extract column name for more helpful message
            match = re.search(r'column "([^"]+)" does not exist', str(e))
            if match:
                bad_column = match.group(1)
                print(f"Column does not exist: {bad_column}")
                
                # Try to extract table name from the query to suggest available columns
                table_match = re.search(r'FROM\s+([^\s]+)', sql_query, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(1)
                    if '.' in table_name:
                        schema, table = table_name.split('.')
                        if (schema in DB_SCHEMA_MAP.get(dbname, {}).get("schemas", {}) and
                            table in DB_SCHEMA_MAP[dbname]["schemas"][schema]["tables"]):
                            columns = list(DB_SCHEMA_MAP[dbname]["schemas"][schema]["tables"][table]["columns"].keys())
                            if columns:
                                print(f"Available columns in {table_name}: {', '.join(columns[:5])}" + 
                                      (", ..." if len(columns) > 5 else ""))
        
        return pd.DataFrame()

def extract_limit_from_query(query):
    """
    Extract a limit value from a natural language query.
    
    Args:
        query (str): Natural language query
        
    Returns:
        int: Extracted limit, -1 for "all" stocks, or None if not found
    """
    query_lower = query.lower()
    
    # Check if user specifically asks for "all" stocks
    all_patterns = [
        r"(?:^|\s)all(?:\s+of)?(?:\s+the)?\s+stocks",
        r"(?:^|\s)all(?:\s+of)?(?:\s+the)?\s+companies",
        r"(?:^|\s)every\s+stock",
        r"(?:^|\s)all\s+results",
        r"(?:^|\s)complete\s+list",
    ]
    
    for pattern in all_patterns:
        if re.search(pattern, query_lower):
            print("User requested ALL stocks (no limit)")
            return -1  # Special code for "all"
    
    # Try to match patterns like "top 10", "limit to 20", "show me 5", etc.
    limit_patterns = [
        r"(?:^|\s)top\s+(\d+)",
        r"(?:^|\s)limit\s+(?:to\s+)?(\d+)",
        r"(?:^|\s)show\s+(?:me\s+)?(\d+)",
        r"(?:^|\s)find\s+(?:the\s+)?(\d+)",  # New pattern for "find the N stocks"
        r"(?:^|\s)(\d+)\s+stocks",
        r"(?:^|\s)(\d+)\s+companies",
        r"(?:^|\s)(\d+)\s+results",
    ]
    
    for pattern in limit_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
                
    return None

def query_database(natural_language_query, limit=5, force_rebuild_schema=False, is_fallback=False):
    """
    Generate and execute a SQL query based on a natural language query.
    
    Args:
        natural_language_query (str): Natural language query
        limit (int, optional): Maximum number of rows to return. Defaults to 5.
        force_rebuild_schema (bool, optional): Force rebuilding the schema map. Defaults to False.
        is_fallback (bool, optional): Whether this is a fallback call. Defaults to False.
        
    Returns:
        pandas.DataFrame: Results of the query
    """
    global DB_SCHEMA_MAP, SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS
    
    # Ensure database schema map is built
    if not DB_SCHEMA_MAP:
        print("Loading database schema map from cache or building if needed...")
        build_database_schema_map(force_rebuild=force_rebuild_schema)
    
    # Ensure keyword maps are built
    if not SECTOR_KEYWORDS or not INDUSTRY_KEYWORDS or not SUBINDUSTRY_KEYWORDS:
        print("Building keyword maps...")
        SECTOR_KEYWORDS, INDUSTRY_KEYWORDS, SUBINDUSTRY_KEYWORDS = build_keyword_maps()
    
    # Try to extract a limit from the query
    extracted_limit = extract_limit_from_query(natural_language_query)
    if extracted_limit is not None:
        limit = extracted_limit
        if limit == -1:
            # User requested "all" results - use a large limit
            limit = 1000
            print(f"Using NO LIMIT (showing up to {limit} results)")
        else:
            print(f"Using limit of {limit} from query")
    else:
        print(f"Using default limit of {limit}")
    
    # Extract query conditions and build WHERE clause
    query_conditions = extract_query_conditions(natural_language_query)
    query_lower = natural_language_query.lower()
    
    # Print extracted conditions for debugging
    if query_conditions:
        print("Query - Extracted conditions:")
        for cond_type, cond_info in query_conditions.items():
            print(f"  - {cond_type}: {cond_info['column']} {cond_info['operator']} {cond_info['value']}")
    else:
        print("Query - No conditions were extracted from the query")
    
    # Build WHERE clause
    where_conditions = []
    for cond_type, cond_info in query_conditions.items():
        where_conditions.append(f"{cond_info['column']} {cond_info['operator']} {cond_info['value']}")
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
        print(f"Query - Using WHERE clause: {where_clause}")
    
    # Automobile/Automotive Industry Query
    if any(term in query_lower for term in ["automobile industry", "automotive industry", "automobiles industry", "car industry", "automotive sector", "automobile sector"]):
        print("Using direct solution for automobile industry query")
        # Handle the special "all" case
        limit_clause = ""
        if limit != 1000:  # Not "all results" case
            limit_clause = f"LIMIT {limit}"
        
        # Determine which columns to include based on conditions
        columns = ["ticker", "short_name", "industry"]
        for cond_type, cond_info in query_conditions.items():
            col = cond_info['column']
            if col not in columns:
                columns.append(col)
        
        # Add default sorting based on conditions
        order_clause = ""
        if "beta_m_3" in columns:
            order_clause = "ORDER BY beta_m_3 ASC"
        elif "alpha_m_3" in columns:
            order_clause = "ORDER BY alpha_m_3 DESC"
        else:
            order_clause = "ORDER BY market_cap DESC"
        
        # First try the automobile manufacturers table
        try:
            sql_query = f"""
            SELECT {', '.join(columns)}
            FROM automobiles.automobile_manufacturers
            {where_clause}
            {order_clause}
            {limit_clause}
            """
            print("Trying automobile manufacturers table")
            results = execute_sql_query(sql_query, dbname="equity_sector_consumer_discretionary")
            if len(results) > 0:
                return results
        except Exception as e:
            print(f"Automobile manufacturers query failed: {str(e)}")
        
        # Then try automobile components as fallback
        try:
            sql_query = f"""
            SELECT {', '.join(columns)}
            FROM automobile_components.automotive_parts_and_equipment
            {where_clause}
            {order_clause}
            {limit_clause}
            """
            print("Trying automobile components table")
            results = execute_sql_query(sql_query, dbname="equity_sector_consumer_discretionary")
            if len(results) > 0:
                return results
        except Exception as e:
            print(f"Automobile components query failed: {str(e)}")
    
    # Enhanced industry detection for automobiles
    if "industry" in query_lower and any(term in query_lower for term in ["automobile", "automotive", "automobiles", "car"]):
        print("Using direct solution for automobiles industry (enhanced detection)")
        # Handle the special "all" case
        limit_clause = ""
        if limit != 1000:  # Not "all results" case
            limit_clause = f"LIMIT {limit}"
        
        # Determine which columns to include based on conditions
        columns = ["ticker", "short_name", "industry"]
        for cond_type, cond_info in query_conditions.items():
            col = cond_info['column']
            if col not in columns:
                columns.append(col)
        
        # Add default sorting based on conditions
        order_clause = ""
        if "beta_m_3" in columns:
            order_clause = "ORDER BY beta_m_3 ASC"
        elif "alpha_m_3" in columns:
            order_clause = "ORDER BY alpha_m_3 DESC"
        else:
            order_clause = "ORDER BY market_cap DESC"
        
        # First try the automobile manufacturers table
        try:
            sql_query = f"""
            SELECT {', '.join(columns)}
            FROM automobiles.automobile_manufacturers
            {where_clause}
            {order_clause}
            {limit_clause}
            """
            print("Trying automobile manufacturers table")
            results = execute_sql_query(sql_query, dbname="equity_sector_consumer_discretionary")
            if len(results) > 0:
                return results
        except Exception as e:
            print(f"Automobile manufacturers query failed: {str(e)}")
        
        # Then try automobile components as fallback
        try:
            sql_query = f"""
            SELECT {', '.join(columns)}
            FROM automobile_components.automotive_parts_and_equipment
            {where_clause}
            {order_clause}
            {limit_clause}
            """
            print("Trying automobile components table")
            results = execute_sql_query(sql_query, dbname="equity_sector_consumer_discretionary")
            if len(results) > 0:
                return results
        except Exception as e:
            print(f"Automobile components query failed: {str(e)}")
    
    # Health Care Query
    if any(term in query_lower for term in ["health", "healthcare", "health care", "medical", "pharma", "pharmaceutical", "biotech"]):
        print("Using direct solution for health care query")
        # Handle the special "all" case
        limit_clause = ""
        if limit != 1000:  # Not "all results" case
            limit_clause = f"LIMIT {limit}"
            
        # Determine which columns to include based on conditions
        columns = ["ticker", "short_name", "industry"]
        for cond_type, cond_info in query_conditions.items():
            col = cond_info['column']
            if col not in columns:
                columns.append(col)
        
        if "market_cap" not in columns:
            columns.append("market_cap")  # Always include market cap for sorting
        
        # Try different health care tables
        healthcare_tables = [
            ("pharmaceuticals.pharmaceuticals", "equity_sector_health_care"),
            ("biotechnology.biotechnology", "equity_sector_health_care"),
            ("health_care_equipment_and_supplies.health_care_equipment", "equity_sector_health_care"),
            ("health_care_providers_and_services.health_care_services", "equity_sector_health_care")
        ]
        
        # Add default sorting if no specific condition-based sorting
        order_clause = "ORDER BY market_cap DESC"  # Default sorting
        
        # Try each table until we get results
        for table_path, dbname in healthcare_tables:
            try:
                schema, table = table_path.split(".")
                sql_query = f"""
                SELECT {', '.join(columns)}
                FROM {schema}.{table}
                {where_clause}
                {order_clause}
                {limit_clause}
                """
                print(f"Trying health care table: {table_path}")
                results = execute_sql_query(sql_query, dbname=dbname)
                if len(results) > 0:
                    return results
            except Exception as e:
                print(f"Error with health care table {table_path}: {str(e)}")
                continue
    
    # Technology Companies
    if "tech" in query_lower or "technology" in query_lower:
        print("Using direct solution for technology companies query")
        # Handle the special "all" case
        limit_clause = ""
        if limit != 1000:  # Not "all results" case
            limit_clause = f"LIMIT {limit}"
            
        # Determine which columns to include based on conditions
        columns = ["ticker", "short_name", "industry"]
        for cond_type, cond_info in query_conditions.items():
            col = cond_info['column']
            if col not in columns:
                columns.append(col)
        
        if "market_cap" not in columns:
            columns.append("market_cap")  # Always include market cap for sorting
        
        # Try multiple tech tables
        tech_tables = [
            "software.application_software",
            "software.software", 
            "it_services.it_services",
            "semiconductors_and_semiconductor_equipment.semiconductors"
        ]
        
        # Add default sorting
        order_clause = "ORDER BY market_cap DESC"
        
        # Try each table until we get results
        for tech_table in tech_tables:
            try:
                schema, table = tech_table.split(".")
                sql_query = f"""
                SELECT {', '.join(columns)}
                FROM {tech_table}
                {where_clause}
                {order_clause}
                {limit_clause}
                """
                print(f"Trying tech table: {tech_table}")
                results = execute_sql_query(sql_query, dbname="equity_sector_information_technology")
                if len(results) > 0:
                    return results
            except Exception as e:
                print(f"Error with tech table {tech_table}: {str(e)}")
                continue
        
        # If we get here, none of the tables worked
        print("All tech tables failed")
    
    # Energy Sector Companies
    if "energy" in query_lower or "oil" in query_lower or "gas" in query_lower:
        print("Using direct solution for energy sector query")
        # Handle the special "all" case
        limit_clause = ""
        if limit != 1000:  # Not "all results" case
            limit_clause = f"LIMIT {limit}"
            
        # Determine which columns to include based on conditions
        columns = ["ticker", "short_name", "industry"]
        for cond_type, cond_info in query_conditions.items():
            col = cond_info['column']
            if col not in columns:
                columns.append(col)
        
        if "market_cap" not in columns:
            columns.append("market_cap")  # Always include market cap for sorting
        
        # Try multiple energy tables
        energy_tables = [
            "oil__gas_and_consumable_fuels.integrated_oil_and_gas",
            "oil__gas_and_consumable_fuels.oil_and_gas_exploration_and_production",
            "energy_equipment_and_services.oil_and_gas_equipment_and_services"
        ]
        
        # Default sorting
        order_clause = "ORDER BY market_cap DESC"
        
        # Try union query first - combining results from multiple tables
        try:
            # Build union query
            union_parts = []
            for table_path in energy_tables:
                union_parts.append(f"""
                (SELECT {', '.join(columns)}
                FROM {table_path}
                {where_clause})
                """)
            
            union_query = " UNION ALL ".join(union_parts)
            sql_query = f"""
            {union_query}
            {order_clause}
            {limit_clause}
            """
            print("Trying energy sector union query")
            results = execute_sql_query(sql_query, dbname="equity_sector_energy")
            if len(results) > 0:
                return results
        except Exception as e:
            print(f"Union query failed: {str(e)}")
        
        # If union query fails, try individual tables
        for energy_table in energy_tables:
            try:
                sql_query = f"""
                SELECT {', '.join(columns)}
                FROM {energy_table}
                {where_clause}
                {order_clause}
                {limit_clause}
                """
                print(f"Trying energy table: {energy_table}")
                results = execute_sql_query(sql_query, dbname="equity_sector_energy")
                if len(results) > 0:
                    return results
            except Exception as e:
                print(f"Error with energy table {energy_table}: {str(e)}")
                continue
    
    # Generate SQL query for other cases
    print(f"Generating SQL query for: {natural_language_query}")
    sql_query = generate_sql_query(natural_language_query)
    
    # Clean SQL query - remove semicolons and ensure proper LIMIT format
    if isinstance(sql_query, str):
        # Remove any existing LIMIT clause
        sql_query = re.sub(r'LIMIT\s+\d+', '', sql_query, flags=re.IGNORECASE).rstrip()
        # Remove trailing semicolon
        sql_query = sql_query.rstrip(';')
        # Add the new LIMIT clause
        sql_query = f"{sql_query} LIMIT {limit}"
    else:
        print(f"Warning: Generated SQL query is not a string: {sql_query}")
        return pd.DataFrame()
    
    # Execute query
    print(f"Executing query...")
    try:
        # Determine the database to use
        dbname, _, _ = get_db_table_for_query(natural_language_query)
        results = execute_sql_query(sql_query, dbname=dbname)
        
        if len(results) == 0 and not is_fallback:
            print("Query returned no results. Using direct fallbacks...")
            # Handle the special "all" case
            limit_clause = ""
            if limit != 1000:  # Not "all results" case
                limit_clause = f"LIMIT {limit}"
            
            # Build WHERE clause from extracted conditions
            where_conditions = []
            for cond_type, cond_info in query_conditions.items():
                where_conditions.append(f"{cond_info['column']} {cond_info['operator']} {cond_info['value']}")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Determine database to use
            dbname, schema_name, table_name = get_db_table_for_query(natural_language_query)
            
            if dbname and schema_name:
                # Determine which columns to include based on conditions
                columns = ["ticker", "short_name", "industry"]
                for cond_type, cond_info in query_conditions.items():
                    col = cond_info['column']
                    if col not in columns:
                        columns.append(col)
                
                if "market_cap" not in columns:
                    columns.append("market_cap")  # Always include market cap for sorting
                
                # Default sorting
                order_clause = "ORDER BY market_cap DESC"
                
                if schema_name in DB_SCHEMA_MAP.get(dbname, {}).get("schemas", {}):
                    # Try all tables in this schema
                    tables = list(DB_SCHEMA_MAP[dbname]["schemas"][schema_name]["tables"].keys())
                    
                    # If we have a specific table, try it first
                    if table_name and table_name in tables:
                        tables.insert(0, tables.pop(tables.index(table_name)))
                    
                    for table in tables:
                        try:
                            sql_query = f"""
                            SELECT {', '.join(columns)}
                            FROM {schema_name}.{table}
                            {where_clause}
                            {order_clause}
                            {limit_clause}
                            """
                            print(f"Trying fallback with table: {schema_name}.{table}")
                            results = execute_sql_query(sql_query, dbname=dbname)
                            if len(results) > 0:
                                return results
                        except Exception as e:
                            print(f"Error with fallback table {schema_name}.{table}: {str(e)}")
                            continue
        
        return results
    except Exception as e:
        print(f"Error in query_database: {str(e)}")
        
        # Last resort fallbacks based on key terms if not already in fallback mode
        if not is_fallback:
            # Handle the special "all" case
            limit_clause = ""
            if limit != 1000:  # Not "all results" case
                limit_clause = f"LIMIT {limit}"
                
            if "automobile" in query_lower or "auto" in query_lower:
                if "parts" in query_lower:
                    sql_query = f"""
                    SELECT ticker, short_name, industry 
                    FROM automobile_components.automotive_parts_and_equipment
                    {where_clause}
                    {limit_clause}
                    """
                else:
                    sql_query = f"""
                    SELECT ticker, short_name, industry, p_e, market_cap 
                    FROM automobiles.automobile_manufacturers
                    ORDER BY market_cap DESC
                    {limit_clause}
                    """
                return execute_sql_query(sql_query, dbname="equity_sector_consumer_discretionary")
                
            if "energy" in query_lower:
                sql_query = f"""
                SELECT ticker, short_name, industry, p_e 
                FROM oil__gas_and_consumable_fuels.integrated_oil_and_gas
                {limit_clause}
                """
                return execute_sql_query(sql_query, dbname="equity_sector_energy")
                
            if "tech" in query_lower or "technology" in query_lower:
                # Try multiple tables that might exist
                for tech_table in ["software.application_software", "software.software", "it_services.it_services"]:
                    try:
                        sql_query = f"""
                        SELECT ticker, short_name, industry, market_cap
                        FROM {tech_table}
                        ORDER BY market_cap DESC
                        {limit_clause}
                        """
                        print(f"Trying final fallback tech table: {tech_table}")
                        results = execute_sql_query(sql_query, dbname="equity_sector_information_technology")
                        if len(results) > 0:
                            return results
                    except Exception as e:
                        print(f"Error with final fallback tech table {tech_table}: {str(e)}")
                        continue
                
                # If we get here, all tables failed
                print("All final fallback tech tables failed")
                return pd.DataFrame()
        
        # If all else fails, return empty DataFrame
        return pd.DataFrame()

def find_matching_phrase(query_text, keywords):
    """
    Find the best matching phrase from a list of keywords in a query text.
    
    Args:
        query_text (str): The text to search in
        keywords (list): List of keyword phrases to match
        
    Returns:
        str: The best matching keyword or None if no match
    """
    print(f"Searching for keyword match in: '{query_text}'")
    query_text = query_text.lower()
    query_words = query_text.split()
    max_match_length = 0
    max_match_score = 0
    best_match = None
    
    # First try exact matches
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in query_text:
            keyword_words = keyword_lower.split()
            if len(keyword_words) > max_match_length:
                max_match_length = len(keyword_words)
                best_match = keyword
                print(f"  Found exact match: '{keyword}'")
    
    # If no exact match, try word sequence matching
    if not best_match:
        for keyword in keywords:
            keyword_lower = keyword.lower()
            keyword_words = keyword_lower.split()
            for i in range(len(query_words) - len(keyword_words) + 1):
                if query_words[i:i + len(keyword_words)] == keyword_words:
                    if len(keyword_words) > max_match_length:
                        max_match_length = len(keyword_words)
                        best_match = keyword
                        print(f"  Found sequence match: '{keyword}'")
    
    # If still no match, try partial matching for common industry terms
    if not best_match:
        # Special case for automobiles
        if any(auto_term in query_text for auto_term in ["auto", "car", "automobile", "automotive"]):
            for keyword in keywords:
                if "automobile" in keyword.lower() or "automotive" in keyword.lower():
                    # Calculate a match score - longer phrases preferred
                    score = len(keyword.split())
                    if score > max_match_score:
                        max_match_score = score
                        best_match = keyword
                        print(f"  Found automobile special match: '{keyword}'")
    
    if best_match:
        print(f"Selected best match: '{best_match}'")
    else:
        print("No keyword match found")
    
    return best_match

# Example usage
if __name__ == "__main__":
    
    try:
        # Load from cache instead of rebuilding
        print("Loading database schema map from cache...")
        build_database_schema_map(force_rebuild=False)
        
        # Test queries
        # print("\nTest Query 1: Find the 3 stocks in the automobile industry with the lowest debt to equity ratio")
        # query = "Find the 3 stocks in the automobile industry with the lowest debt to equity ratio"
        # results = query_database(query)  # Should extract limit=3 from query
        # print(results)

        # print("\nTest Query 2: Find me the top 7 stocks in the energy sector with pe higher than 20")
        # query = "Find me the top 7 stocks in the energy sector with pe higher than 20"
        # results = query_database(query)  # Should extract limit=7 from query
        # print(results)
        
        # print("\nTest Query 3: Find me stocks in the automobile parts sub industry")
        # query = "Find me stocks in the automobile parts sub industry"
        # results = query_database(query)  # Should use default limit=5
        # print(results)
        
        # print("\nTest Query 4: Show me 10 tech companies with the highest market cap")
        # query = "Show me 10 tech companies with the highest market cap"
        # results = query_database(query)  # Should extract limit=10 from query
        # print(results)

        while True:
            query = input("Enter a query: ")
            results = query_database(query)
            print(results)
        
    except Exception as e:
        print(f"Error: {str(e)}")