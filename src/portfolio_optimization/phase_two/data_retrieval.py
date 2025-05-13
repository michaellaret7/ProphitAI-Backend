import os
import pandas as pd
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from finvizfinance.quote import finvizfinance
import json 

# Import from utils package
from src.utils.caching import cache_result
from src.utils.file_utils import load_schema_data
from src.utils.database import get_default_db_config

# Move this to utils 
@cache_result
def get_daily_closing_prices(ticker, years=4, db_config=None):
   """
   Retrieve daily closing prices (last bar of each day) for a given stock
   """
   # Database configuration
   if db_config is None:
      db_config = get_default_db_config()
   
   # Normalize ticker
   ticker_upper = ticker.upper()
   ticker_lower = ticker.lower()
   
   # Calculate start date
   end_date = datetime.now()
   start_date = end_date - timedelta(days=365 * years)
   
   # Load schema definition
   schema_data = load_schema_data()
   
   # Find ticker location
   ticker_location = None
   for sector_name, sector_info in schema_data.items():
      database = sector_info.get('database')
      schemas = sector_info.get('schemas', {})
      
      for schema_name, schema_info in schemas.items():
         tables = schema_info.get('tables', {})
         
         for table_name, table_info in tables.items():
               tickers = table_info.get('tickers', [])
               
               # Case-insensitive comparison
               for db_ticker in tickers:
                  if ticker_upper.upper() == db_ticker.upper():
                     # Special case for ETFs - use specific database names
                     if "etf" in sector_name.lower():
                        db_name = "etf_prices"
                     else:
                        db_name = f"{database}_prices"
                        
                     ticker_location = {
                        "database": db_name,
                        "schema": f"{schema_name}_prices",
                        "ticker": db_ticker  # Use the ticker with the exact case from the database
                     }

                     break
         if ticker_location: break
      if ticker_location: break
   
   if not ticker_location:
      # Just pass silently if ticker not found
      return None
   
   try:
      # Connect to database
      db_config['dbname'] = ticker_location['database']
      conn = psycopg2.connect(**db_config)
      cursor = conn.cursor()
      
      # Query only the last bar of each day for close price, and sum daily volume
      # Use window functions for efficiency
      query = f"""
      WITH ranked_data AS (
          SELECT 
              datetime,
              CAST(date AS DATE) as trading_date,
              close,
              volume,
              ROW_NUMBER() OVER(PARTITION BY CAST(date AS DATE) ORDER BY datetime DESC) as rn,
              SUM(volume) OVER(PARTITION BY CAST(date AS DATE)) as daily_total_volume
          FROM {ticker_location['schema']}.{ticker_lower}
          WHERE date >= %s
      )
      SELECT 
         trading_date as date,
         close,
         daily_total_volume as volume
      FROM ranked_data
      WHERE rn = 1 -- Select only the last bar's row for each day
      ORDER BY trading_date ASC
      """
      
      cursor.execute(query, (start_date.strftime('%Y-%m-%d'),))
      
      # Convert results
      results = []
      for row in cursor.fetchall():
         date_val, close_val, volume_val = row # Added volume_val
         
         if isinstance(close_val, Decimal):
               close_val = float(close_val)
               
         # Ensure volume is an integer
         if volume_val is None:
             volume_val = 0
         elif isinstance(volume_val, Decimal):
             volume_val = int(volume_val)
         elif isinstance(volume_val, float):
              volume_val = int(volume_val)
             
         results.append({
               "date": date_val.strftime('%Y-%m-%d'),
               "close": close_val,
               "volume": volume_val # Added volume
         })

      df = pd.DataFrame(results)
      df['date'] = pd.to_datetime(df['date'])
      # Keep sorting as a safety net
      df = df.sort_values('date')

      return df
      
   except Exception as e:
      # Just pass silently on error
      return None
   
   finally:
      if 'conn' in locals() and conn:
         cursor.close()
         conn.close()

# move this to utils
@cache_result
def get_fundamentals_data(ticker, db_config=None):
   """
   Retrieve all fundamental data for a given stock across different tables
   (balance sheets, cash flow statements, financial metrics, etc.)
   """
   # Database configuration
   if db_config is None:
      db_config = get_default_db_config()
   
   # Normalize ticker
   ticker_upper = ticker.upper()
   ticker_lower = ticker.lower()
   
   # Load schema definition
   schema_data = load_schema_data()
   
   # Find ticker location
   ticker_location = None
   for sector_name, sector_info in schema_data.items():
      database = sector_info.get('database')
      schemas = sector_info.get('schemas', {})
      
      for schema_name, schema_info in schemas.items():
         tables = schema_info.get('tables', {})
         
         for table_name, table_info in tables.items():
               tickers = table_info.get('tickers', [])
               
               if ticker_upper in tickers:
                  # Special case for ETFs - use specific database names
                  if "etf" in sector_name.lower():
                     db_name = database # Use the database name defined in the schema file
                  else:
                     db_name = f"{database}_fundamentals"
                     
                  ticker_location = {
                     "database": db_name,
                     "schema": f"{schema_name}",
                     "ticker": ticker_upper
                  }
                  break
         if ticker_location: break
      if ticker_location: break
   
   # If the ticker is identified as an ETF, return empty data immediately
   # Assumes 'etf_data' is the database name designated for ETFs in database_schemas.json
   if ticker_location and ticker_location.get('database') == 'etf_data':
      print(f"Ticker {ticker_upper} identified as ETF, skipping fundamental data retrieval.")
      return {}
   
   if not ticker_location:
      # Try case-insensitive ticker search if exact match wasn't found
      for sector_name, sector_info in schema_data.items():
         database = sector_info.get('database')
         schemas = sector_info.get('schemas', {})
         
         for schema_name, schema_info in schemas.items():
            tables = schema_info.get('tables', {})
            
            for table_name, table_info in tables.items():
                  tickers = table_info.get('tickers', [])
                  
                  # Case-insensitive comparison
                  for db_ticker in tickers:
                     if ticker_upper.upper() == db_ticker.upper():
                        # Special case for ETFs - use specific database names
                        if "etf" in sector_name.lower():
                           db_name = database # Use the database name defined in the schema file
                        else:
                           db_name = f"{database}_fundamentals"
                           
                        ticker_location = {
                           "database": db_name,
                           "schema": f"{schema_name}",
                           "ticker": db_ticker  # Use the ticker with the exact case from the database
                        }
                        break
            if ticker_location: break # Added break
         if ticker_location: break # Added break
   
   if not ticker_location:
      print(f"Ticker {ticker_upper} not found in any database schema for fundamentals.") # Modified print message
      return None
   
   try:
      # Connect to database
      db_config['dbname'] = ticker_location['database']
      conn = psycopg2.connect(**db_config)
      cursor = conn.cursor()
      
      # Define fundamental table types
      table_types = [
         "balance_sheets",
         "cash_flow_statements", 
         "financial_metrics",
         "income_statements"
      ]
      
      # Dictionary to store all fundamental data
      fundamental_data = {}
      
      # Large number columns that should have comma formatting
      large_number_columns = [
         'market_cap', 'revenue', 'total_assets', 'total_liabilities', 
         'total_equity', 'total_debt', 'net_income', 'operating_income',
         'gross_profit', 'ebitda', 'cash_flow', 'capex', 'fcf', 'dividends_paid',
         'shares_outstanding', 'total_cash', 'current_assets', 'current_liabilities'
      ]
      
      # Query each table type
      for table_type in table_types:
         table_name = f"{ticker_lower}_{table_type}"
         
         try:
            # Check if table exists
            check_query = f"""
            SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_schema = '{ticker_location['schema']}'
               AND table_name = '{table_name}'
            )
            """
            cursor.execute(check_query)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
               print(f"Table {table_name} does not exist, skipping")
               continue
            
            # First check if data exists from 2015
            check_data_query = f"""
            SELECT COUNT(*) 
            FROM {ticker_location['schema']}.{table_name}
            WHERE date >= '2015-01-01'
            """
            cursor.execute(check_data_query)
            data_count = cursor.fetchone()[0]
            
            # Query table data - from 2015 if data exists, otherwise all data
            if data_count > 0:
               query = f"""
               SELECT *
               FROM {ticker_location['schema']}.{table_name}
               WHERE date >= '2015-01-01'
               ORDER BY date
               """
            else:
               # Fallback to all data if no data from 2015
               query = f"""
               SELECT *
               FROM {ticker_location['schema']}.{table_name}
               ORDER BY date
               """
            
            cursor.execute(query)
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            
            # Convert results
            results = []
            for row in cursor.fetchall():
               # Convert row to dict
               row_dict = {}
               for i, value in enumerate(row):
                  col_name = column_names[i]
                  # Convert Decimal to float
                  if isinstance(value, Decimal) or isinstance(value, float):
                     value = float(value)
                  row_dict[col_name] = value
                     
               results.append(row_dict)
            
            # Create DataFrame and handle data types
            df = pd.DataFrame(results)
            
            # Process dates
            if 'date' in df.columns and not df.empty:
               df['date'] = pd.to_datetime(df['date'])
               df = df.sort_values('date')
            
            # Process numeric columns
            for col in df.columns:
               # Skip date and non-numeric columns
               if col == 'date' or col == 'ticker' or col == 'currency' or col == 'period' or col == 'report_period' or col == 'calendar_date':
                  continue
                  
               # Convert to numeric and round
               try:
                  df[col] = pd.to_numeric(df[col], errors='coerce')
                  df[col] = df[col].round(2)
               except:
                  # Keep as is if conversion fails
                  pass
            
            # Convert DataFrame to formatted dictionary
            formatted_data = []
            for _, row in df.iterrows():
               formatted_row = {}
               for col, val in row.items():
                  # Format date columns to ISO format
                  if col == 'date' and pd.notna(val):
                     formatted_row[col] = val.strftime('%Y-%m-%d')
                  # Keep numeric values as actual numbers for better LLM analysis
                  elif pd.api.types.is_numeric_dtype(type(val)) and pd.notna(val):
                     formatted_row[col] = float(val) if col.lower() not in large_number_columns else int(val)
                  # Handle any other values including NaN/None
                  else:
                     formatted_row[col] = str(val) if pd.notna(val) else None
               
               formatted_data.append(formatted_row)
            
            # Add to the fundamental data dictionary
            fundamental_data[table_type] = formatted_data
            
         except Exception as e:
            print(f"Error retrieving {table_type} data: {e}")
            fundamental_data[table_type] = []  # Empty list as fallback
      
      return fundamental_data
      
   except Exception as e:
      print(f"Error retrieving fundamental data: {e}")
      return None
   
   finally:
      if 'conn' in locals() and conn:
         cursor.close()
         conn.close()

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

# HAVE THIS RETRIEVE FROM DB TO GET RID OF ALL RELIANCE ON IBKR. IF NOT IN DB JUST RETURN NOT IN DB
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

    db_cfg["dbname"] = db_name

    try:
        conn = psycopg2.connect(**db_cfg)
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

    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

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


if __name__ == "__main__":
    print(get_quarterly_estimates("AAPL"))