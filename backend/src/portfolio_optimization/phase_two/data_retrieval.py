import os
import pandas as pd
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from finvizfinance.quote import finvizfinance
import json 

# Import from utils package
from backend.src.utils.caching import cache_result
from backend.src.utils.file_utils import load_schema_data
from backend.src.utils.database import get_default_db_config, get_db_connection
from backend.src.utils.data_retrieval import get_price_data, get_fundamental_data

# Create wrapper functions for backward compatibility
def get_daily_closing_prices(ticker, years=4, db_config=None):
   """
    Wrapper function for backward compatibility.
    Retrieves daily closing prices using the generic get_price_data function.
    """
   return get_price_data(ticker, frequency='daily', years=years, db_config=db_config)

def get_fundamentals_data(ticker, db_config=None):
   """
    Wrapper function for backward compatibility.
    Retrieves fundamental data using the generic get_fundamental_data function.
    """
   return get_fundamental_data(ticker, db_config=db_config)

@cache_result
def get_stock_tickers(asset_class):
    """
    Retrieve stock tickers from database_schemas.json filtered by a value.
    The function automatically determines if the filter value is a sector, industry, or subindustry.
    
    Args:
        filter_value (str, optional): Value to filter on. If None, returns all tickers.
    
    Returns:
        dict: Dictionary with filter_value as key and list of matching stock tickers as value
    """
    schema_data = load_schema_data()
    
    # List to store all matching tickers
    matching_tickers = []
    
    # If no filter is provided, return all tickers
    if asset_class is None:
        for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            for schema_name, schema_info in schemas.items():
                tables = schema_info.get('tables', {})
                
                for table_name, table_info in tables.items():
                    tickers = table_info.get('tickers', [])
                    matching_tickers.extend(tickers)
                    
        return {"all": matching_tickers}
    
    # Check if filter_value is a sector
    if asset_class in schema_data:
        # Filter by sector
        sector_info = schema_data[asset_class]
        schemas = sector_info.get('schemas', {})
        
        for schema_name, schema_info in schemas.items():
            tables = schema_info.get('tables', {})
            
            for table_name, table_info in tables.items():
                tickers = table_info.get('tickers', [])
                matching_tickers.extend(tickers)
    else:
        # Check for industry or subindustry match
        for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            for schema_name, schema_info in schemas.items():
                # Check if schema name matches the filter (industry)
                if schema_name == asset_class:
                    tables = schema_info.get('tables', {})
                    for table_name, table_info in tables.items():
                        tickers = table_info.get('tickers', [])
                        matching_tickers.extend(tickers)
                
                # Check for subindustry match in table names
                tables = schema_info.get('tables', {})
                for table_name, table_info in tables.items():
                    if table_name == asset_class:
                        tickers = table_info.get('tickers', [])
                        matching_tickers.extend(tickers)
    
    # Remove duplicates and sort list
    sorted_tickers = sorted(list(set(matching_tickers)))
    
    # Return dictionary with filter_value as key and ticker list as value
    return {asset_class: sorted_tickers}

def get_quarterly_estimates(ticker: str) -> str:
    """Return quarterly fundamental estimates for *ticker* from Postgres as JSON.

    The estimates are pre-fetched from Interactive Brokers (via
    ``update_fundamental_predictions.py``) and stored in the database following
    this naming convention:

    * database:     ``<sector_db>_fundamentals`` (e.g. ``equity_sector_technology_fundamentals``)
    * schema:       ``<industry>``            (e.g. ``semiconductors``)
    * table:        ``<ticker>_fundamental_estimates`` (lower-case ticker)

    The helper resolves the correct location via ``database_schemas.json`` (same
    lookup logic as ``get_fundamentals_data``).  If the table exists its full
    content is returned as the key ``"quarterly_estimates"`` – identical output
    shape as the previous IBKR implementation so callers remain unchanged.

    When the ticker cannot be located, the table is missing, or any database
    error occurs the function returns ``{"error": "…"}`` instead.
    """

    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()

    # ------------------------------------------------------------------
    # 1. Locate ticker within schema definition
    # ------------------------------------------------------------------
    schema_data = load_schema_data()
    if not schema_data:
        return json.dumps({"error": "Could not load database schema definitions."})

    ticker_location = None

    # First pass – case-sensitive lookup (faster)
    for sector_name, sector_info in schema_data.items():
        database = sector_info.get("database")
        for schema_name, schema_info in sector_info.get("schemas", {}).items():
            for table_info in schema_info.get("tables", {}).values():
                if ticker_upper in table_info.get("tickers", []):
                    if "etf" in sector_name.lower():
                        db_name = database  # ETFs stored in dedicated db (skip estimates)
                    else:
                        db_name = f"{database}_fundamentals"
                    ticker_location = {
                        "database": db_name,
                        "schema": schema_name,
                        "sector": sector_name,
                    }
                    break
            if ticker_location:
                break
        if ticker_location:
            break

    # Fallback – case-insensitive search
    if not ticker_location:
        for sector_name, sector_info in schema_data.items():
            database = sector_info.get("database")
            for schema_name, schema_info in sector_info.get("schemas", {}).items():
                for table_info in schema_info.get("tables", {}).values():
                    for db_ticker in table_info.get("tickers", []):
                        if db_ticker.upper() == ticker_upper:
                            if "etf" in sector_name.lower():
                                db_name = database
                            else:
                                db_name = f"{database}_fundamentals"
                            ticker_location = {
                                "database": db_name,
                                "schema": schema_name,
                                "sector": sector_name,
                            }
                            break
                    if ticker_location:
                        break
            if ticker_location:
                break

    # ETFs have no fundamental estimates – short-circuit
    if ticker_location and ticker_location["database"] == "etf_data":
        return json.dumps({"error": f"{ticker_upper} is an ETF – no fundamental estimates available."})

    if not ticker_location:
        return json.dumps({"error": f"Ticker {ticker_upper} not found in schema definitions."})

    # ------------------------------------------------------------------
    # 2. Build fully-qualified table reference
    # ------------------------------------------------------------------
    table_name = f"{ticker_lower}_fundamental_estimates"
    db_name = ticker_location["database"]
    schema_name = ticker_location["schema"]

    # ------------------------------------------------------------------
    # 3. Connect & fetch data
    # ------------------------------------------------------------------
    db_cfg = get_default_db_config()
    if not db_cfg or not all(db_cfg.values()):
        return json.dumps({"error": "Database connection information missing in environment."})

    try:
        with get_db_connection(db_name, db_cfg) as conn:
            cursor = conn.cursor()

            # Check table existence first to avoid ugly errors
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                );""",
                (schema_name, table_name),
            )
            if not cursor.fetchone()[0]:
                return json.dumps({"error": f"Fundamental estimates table not found for {ticker_upper}."})

            # Pull everything (the data already starts at Q2-2025 per loader script)
            cursor.execute(
                f"SELECT * FROM {schema_name}.{table_name} ORDER BY year, quarter;"
            )
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]

            if not rows:
                return json.dumps({"error": f"No fundamental estimates stored for {ticker_upper}."})

            # Build DataFrame and tidy types
            df = pd.DataFrame(rows, columns=cols)

            # Convert Decimals → float; integers keep as is
            for col in df.columns:
                if col in ("year", "quarter"):
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Optional safety-filter again (Q2-2025 onwards)
            df = df[(df["year"] > 2025) | ((df["year"] == 2025) & (df["quarter"] >= 2))]

            # Rename columns back to original format expected by downstream code
            rename_map = {"year": "Year", "quarter": "Quarter"}
            for col in df.columns:
                if col not in ("year", "quarter"):
                    rename_map[col] = col.upper()
            df.rename(columns=rename_map, inplace=True)

            # Ensure Year and Quarter are plain Python ints for JSON serialisation
            if "Year" in df.columns:
                df["Year"] = df["Year"].astype(int)
            if "Quarter" in df.columns:
                df["Quarter"] = df["Quarter"].astype(int)

            results_data = {"quarterly_estimates": []}

            if not df.empty:
                results_data["quarterly_estimates"] = df.to_dict(orient="records")

            return json.dumps(results_data)

    except Exception as e:
        return json.dumps({"error": f"Database error while retrieving estimates for {ticker_upper}: {e}"})

def get_asset_description(ticker):

    # Create a finvizfinance object for the ETF
    etf = finvizfinance(ticker)

    # Get only the description of the ETF
    etf_description = etf.ticker_description()

    # Print the description
    # print(etf_description) # Removed print, function should just return

    return etf_description

def extract_asset_classes(json_data):
    """
    Extract asset classes from portfolio JSON data.
    
    Args:
        json_data (dict): JSON data containing portfolio data
        
    Returns:
        dict: Dictionary mapping asset classes to their allocations, with 'cash' filtered out
    """
    # Parse the JSON string
    data = json_data
    
    # Check if data has expected structure
    if not isinstance(data, dict):
        print("Error: Portfolio data is not a dictionary")
        return {}
    
    if "portfolio" not in data:
        print("Error: Portfolio data does not contain 'portfolio' key")
        return {}
    
    if not isinstance(data["portfolio"], list) or not data["portfolio"]:
        print("Error: Portfolio array is empty or not a list")
        return {}
    
    # Extract asset classes with allocations
    asset_classes = {}
    for item in data["portfolio"]:
        if not isinstance(item, dict):
            print(f"Warning: Portfolio item is not a dictionary: {item}")
            continue
            
        asset_class = item.get("asset_class")
        allocation = item.get("allocation")
        
        if not asset_class:
            print(f"Warning: Missing 'asset_class' in portfolio item: {item}")
            continue
            
        if allocation is None:
            print(f"Warning: Missing 'allocation' in portfolio item: {item}")
            continue
        
        # Convert allocation to float if it's a string (handle % if present)
        if isinstance(allocation, str):
            allocation = float(allocation.strip("%"))
        
        asset_classes[asset_class] = allocation
    
    # Filter out 'cash' from the dictionary
    asset_classes = {k: v for k, v in asset_classes.items() if k.lower() != 'cash'}
    
    if not asset_classes:
        print("Warning: No valid asset classes found in portfolio data")
        
    return asset_classes

