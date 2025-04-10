import os
import psycopg2
import json
import pandas as pd
from decimal import Decimal
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

load_dotenv()

def get_fundamentals_data(ticker, db_config=None):
   """
   Retrieve all fundamental data for a given stock across different tables
   (balance sheets, cash flow statements, financial metrics, etc.)
   """
   # Database configuration
   if db_config is None:
      db_config = {
         "host": os.environ.get("DB_HOST"),
         "user": os.environ.get("DB_USER"),
         "password": os.environ.get("DB_PASSWORD"),
         "port": os.environ.get("DB_PORT")
      }
   
   # Normalize ticker
   ticker_upper = ticker.upper()
   ticker_lower = ticker.lower()
   
   # Load schema definition
   with open('database_schemas.json', 'r') as f:
      schema_data = json.load(f)
   
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
                     db_name = "etf_fundamentals"
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
                           db_name = "etf_fundamentals"
                        else:
                           db_name = f"{database}_fundamentals"
                           
                        ticker_location = {
                           "database": db_name,
                           "schema": f"{schema_name}",
                           "ticker": db_ticker  # Use the ticker with the exact case from the database
                        }
                        break
   
   if not ticker_location:
      print(f"Ticker {ticker_upper} not found")
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
            
            # Query all data from table without date filtering
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

def get_most_recent_piotroski_score(ticker):
    """
    Calculate the most recent Piotroski Score for a given stock ticker based on available financial data.
    
    Parameters:
    - ticker (str): The stock ticker symbol (e.g., "AAPL").
    
    Returns:
    - tuple: (score, fiscal_year) where score is the Piotroski Score (0-7) or None if data is insufficient,
             and fiscal_year is the year for which it was calculated or None.
    
    Note: Assumes fiscal year ends in September (e.g., Apple's fiscal calendar). Due to missing cash flow data,
          the score is based on 7 criteria instead of the full 9.
    """
    # Retrieve fundamentals data (assuming get_fundamentals_data is defined elsewhere)
    data = get_fundamentals_data(ticker)
    if data is None or 'balance_sheets' not in data or 'income_statements' not in data:
        return None, None
    
    # Convert data into DataFrames
    balance_df = pd.DataFrame(data['balance_sheets'])
    income_df = pd.DataFrame(data['income_statements'])
    
    # Parse dates and set as index
    balance_df['date'] = pd.to_datetime(balance_df['date'])
    income_df['date'] = pd.to_datetime(income_df['date'])
    balance_df.set_index('date', inplace=True)
    income_df.set_index('date', inplace=True)
    
    # Identify all fiscal years with September balance sheets
    sept_years = balance_df[balance_df.index.month == 9].index.year.unique()
    sept_years = sorted(sept_years, reverse=True)  # Sort descending to start with most recent
    
    # Iterate over fiscal years to find the most recent one with complete data
    for year in sept_years:
        # Define quarter dates for current and previous fiscal years (Apple's FY ends in September)
        current_quarters = [
            pd.Timestamp(year - 1, 12, 31),  # Q1
            pd.Timestamp(year, 3, 31),       # Q2
            pd.Timestamp(year, 6, 30),       # Q3
            pd.Timestamp(year, 9, 30)        # Q4
        ]
        previous_quarters = [
            pd.Timestamp(year - 2, 12, 31),  # Q1 previous year
            pd.Timestamp(year - 1, 3, 31),   # Q2 previous year
            pd.Timestamp(year - 1, 6, 30),   # Q3 previous year
            pd.Timestamp(year - 1, 9, 30)    # Q4 previous year
        ]
        
        # Check if all required income statement quarters exist
        if not all(q in income_df.index for q in current_quarters + previous_quarters):
            continue
        
        # Define balance sheet dates (current and two prior years)
        current_q4 = pd.Timestamp(year, 9, 30)
        previous_q4 = pd.Timestamp(year - 1, 9, 30)
        two_years_ago_q4 = pd.Timestamp(year - 2, 9, 30)
        
        # Check if all required balance sheets exist
        if not all(q in balance_df.index for q in [current_q4, previous_q4, two_years_ago_q4]):
            continue
        
        # Extract income statement data
        current_net_income = income_df.loc[current_quarters, 'net_income'].sum()
        previous_net_income = income_df.loc[previous_quarters, 'net_income'].sum()
        current_revenue = income_df.loc[current_quarters, 'revenue'].sum()
        previous_revenue = income_df.loc[previous_quarters, 'revenue'].sum()
        current_gross_profit = income_df.loc[current_quarters, 'gross_profit'].sum()
        previous_gross_profit = income_df.loc[previous_quarters, 'gross_profit'].sum()
        
        # Extract balance sheet data
        current_bs = balance_df.loc[current_q4]
        previous_bs = balance_df.loc[previous_q4]
        two_years_ago_bs = balance_df.loc[two_years_ago_q4]
        
        current_total_assets = current_bs['total_assets']
        previous_total_assets = previous_bs['total_assets']
        two_years_ago_total_assets = two_years_ago_bs['total_assets']
        current_long_term_debt = current_bs['non_current_debt']
        previous_long_term_debt = previous_bs['non_current_debt']
        current_current_assets = current_bs['current_assets']
        previous_current_assets = previous_bs['current_assets']
        current_current_liabilities = current_bs['current_liabilities']
        previous_current_liabilities = previous_bs['current_liabilities']
        current_outstanding_shares = current_bs['outstanding_shares']
        previous_outstanding_shares = previous_bs['outstanding_shares']
        
        # Calculate Piotroski Score (7 criteria)
        score = 0
        
        # Profitability Criteria
        if current_net_income > 0:
            score += 1
        if current_net_income / previous_total_assets > 0:
            score += 1
        
        # Leverage, Liquidity, and Source of Funds Criteria
        current_debt_ratio = current_long_term_debt / current_total_assets if current_total_assets != 0 else 0
        previous_debt_ratio = previous_long_term_debt / previous_total_assets if previous_total_assets != 0 else 0
        if current_debt_ratio < previous_debt_ratio:
            score += 1
        
        current_current_ratio = current_current_assets / current_current_liabilities if current_current_liabilities != 0 else float('inf')
        previous_current_ratio = previous_current_assets / previous_current_liabilities if previous_current_liabilities != 0 else float('inf')
        if current_current_ratio > previous_current_ratio:
            score += 1
        
        if current_outstanding_shares <= previous_outstanding_shares:
            score += 1
        
        # Operating Efficiency Criteria
        current_gross_margin = current_gross_profit / current_revenue if current_revenue != 0 else 0
        previous_gross_margin = previous_gross_profit / previous_revenue if previous_revenue != 0 else 0
        if current_gross_margin > previous_gross_margin:
            score += 1
        
        current_asset_turnover = current_revenue / previous_total_assets if previous_total_assets != 0 else 0
        previous_asset_turnover = previous_revenue / two_years_ago_total_assets if two_years_ago_total_assets != 0 else 0
        if current_asset_turnover > previous_asset_turnover:
            score += 1
        
        # Return the score and year as soon as a valid score is calculated
        return score, year
    
    # Return None if no fiscal year has complete data
    return None, None


