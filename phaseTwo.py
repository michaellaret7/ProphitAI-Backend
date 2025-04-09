import os
import json
import pandas as pd
import numpy as np
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import concurrent.futures

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

model = 'deepseek-reasoner'

# Sample portfolio data for testing when this module is run directly
portfolio_data = {
  "portfolio": [
    {
      "asset_class": "precious_metals_etfs",
      "allocation": 15,
      "reason": "Growth potential driven by AI and cloud technologies."
    },

    {
      "asset_class": "automobile_manufacturers",
      "allocation": 5,
      "reason": "Attractive yields amid low interest rates."
    },
    {
      "asset_class": "cash",
      "allocation": 5,
      "reason": "For liquidity and opportunistic investments."
    }
  ]
}


def get_daily_closing_prices(ticker, years=4, db_config=None):
   """
   Retrieve daily closing prices (last bar of each day) for a given stock
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
   
   # Calculate start date
   end_date = datetime.now()
   start_date = end_date - timedelta(days=365 * years)
   
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
      
      # Query only the last bar of each day
      query = f"""
      WITH daily_closing AS (
         SELECT 
               CAST(date AS DATE) as trading_date,
               MAX(datetime) as last_bar_time
         FROM {ticker_location['schema']}.{ticker_lower}
         WHERE date >= %s
         GROUP BY CAST(date AS DATE)
      )
      SELECT 
         dc.trading_date as date,
         t.close
      FROM daily_closing dc
      JOIN {ticker_location['schema']}.{ticker_lower} t
         ON t.datetime = dc.last_bar_time
      ORDER BY dc.trading_date DESC
      """
      
      cursor.execute(query, (start_date.strftime('%Y-%m-%d'),))
      
      # Convert results
      results = []
      for row in cursor.fetchall():
         date_val, close_val = row
         
         if isinstance(close_val, Decimal):
               close_val = float(close_val)
               
         results.append({
               "date": date_val.strftime('%Y-%m-%d'),
               "close": close_val
         })

      df = pd.DataFrame(results)
      df['date'] = pd.to_datetime(df['date'])
      df = df.sort_values('date')

      return df
      
   except Exception as e:
      # Just pass silently on error
      return None
   
   finally:
      if 'conn' in locals() and conn:
         cursor.close()
         conn.close()

def calculate_stock_metrics(ticker):
   """
   Calculate the Sharpe ratio and other risk-adjusted performance metrics for a stock.
   
   Args:
       ticker (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT')
   
   Returns:
       dict: Dictionary containing calculated financial metrics
   """
   # Get price data for the ticker
   price_data = get_daily_closing_prices(ticker)
   spy_data = get_daily_closing_prices('spy')
   
   # Check if ticker is an ETF (simple check based on common ETF tickers from screenshot)
   etf_list = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC"]
   is_etf = ticker.upper() in etf_list
   
   # Return default values if no price data is available
   if price_data is None:
      print(f"No price data available for {ticker}")
      default_metrics = {
         "ticker": ticker,
         "sharpe_ratio": 0,
         "sortino_ratio": 0,
         "calmar_ratio": 0,
         "annualized_return": 0,
         "annualized_volatility": 0,
         "daily_return_volatility": 0,
         "max_drawdown": 0,
         "beta": 0,
         "date_range": [],
         "upside_capture": 0,
         "downside_capture": 0,
         "momentum_6m": 0,
         "momentum_12m": 0
      }
      
      # Only add sector fields for non-ETFs
      if not is_etf:
         default_metrics.update({
            "sector_beta": 0
         })
      
      return default_metrics
   
   risk_free_rate=0.03
   annualization_factor=252
   df = price_data
   df['daily_return'] = df['close'].pct_change()
   
   # Drop NaN values (first row will have NaN return) and create an explicit copy
   df = df.dropna().copy()
   
   # Calculate metrics
   daily_returns = df['daily_return'].values
   mean_daily_return = np.mean(daily_returns)
   std_daily_return = np.std(daily_returns)
   
   # Calculate Momentum Scores (6-month and 12-month)
   momentum_6m = 0
   momentum_12m = 0
   
   # Check if we have enough data points for momentum calculations
   if len(df) >= 126:  # 6 months
      # Take the last 126 trading days for 6-month momentum
      recent_returns_6m = df['daily_return'].iloc[-126:]
      momentum_6m = (1 + recent_returns_6m).prod() - 1
   
   if len(df) >= 252:  # 12 months / 1 year
      # Take the last 252 trading days for 12-month momentum
      recent_returns_12m = df['daily_return'].iloc[-252:]
      momentum_12m = (1 + recent_returns_12m).prod() - 1
   
   # Convert risk-free rate to daily
   daily_risk_free_rate = (1 + risk_free_rate) ** (1/annualization_factor) - 1
   
   # Calculate daily Sharpe ratio
   daily_sharpe = (mean_daily_return - daily_risk_free_rate) / std_daily_return if std_daily_return > 0 else 0
   
   # Annualize Sharpe ratio
   annual_sharpe = daily_sharpe * np.sqrt(annualization_factor)
   
   # Calculate annualized return and volatility
   annual_return = ((1 + mean_daily_return) ** annualization_factor) - 1
   annual_volatility = std_daily_return * np.sqrt(annualization_factor)
   
   # Calculate Maximum Drawdown
   df['cumulative_return'] = (1 + df['daily_return']).cumprod()
   df['rolling_max'] = df['cumulative_return'].cummax()
   df['drawdown'] = (df['cumulative_return'] / df['rolling_max']) - 1
   max_drawdown = df['drawdown'].min()
   
   # Calculate Sortino Ratio (uses only negative returns to penalize downside deviation)
   negative_returns = daily_returns[daily_returns < 0]
   downside_deviation = np.std(negative_returns) if len(negative_returns) > 0 else 0
   sortino_ratio = 0
   if downside_deviation > 0:
      sortino_ratio = (mean_daily_return - daily_risk_free_rate) / downside_deviation * np.sqrt(annualization_factor)
   
   # Calculate Calmar Ratio (return / maximum drawdown)
   calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else 0
   
   # Calculate Beta (market risk)
   beta = 0
   if spy_data is not None:
      spy_df = spy_data
      spy_df['daily_return'] = spy_df['close'].pct_change()
      spy_df = spy_df.dropna()
      
      # Align the dates between stock and market data
      merged_data = pd.merge(
         df[['date', 'daily_return']], 
         spy_df[['date', 'daily_return']], 
         on='date', 
         how='inner',
         suffixes=('_stock', '_market')
      )
      
      if not merged_data.empty:
         # Calculate beta as covariance / variance
         covariance = np.cov(merged_data['daily_return_stock'], merged_data['daily_return_market'])[0, 1]
         market_variance = np.var(merged_data['daily_return_market'])
         if market_variance > 0:
            beta = covariance / market_variance
            
         # Calculate Upside and Downside Capture Ratios
         # Identify up and down market days
         up_days = merged_data[merged_data['daily_return_market'] > 0]
         down_days = merged_data[merged_data['daily_return_market'] < 0]
         
         # Default values
         upside_capture = 0
         downside_capture = 0
         
         # Calculate Upside Capture Ratio
         if not up_days.empty and up_days['daily_return_market'].mean() > 0:
            avg_stock_return_up = up_days['daily_return_stock'].mean()
            avg_benchmark_return_up = up_days['daily_return_market'].mean()
            upside_capture = avg_stock_return_up / avg_benchmark_return_up
         
         # Calculate Downside Capture Ratio
         if not down_days.empty and down_days['daily_return_market'].mean() < 0:
            avg_stock_return_down = down_days['daily_return_stock'].mean()
            avg_benchmark_return_down = down_days['daily_return_market'].mean()
            downside_capture = avg_stock_return_down / avg_benchmark_return_down
   
   # Initialize sector-specific variables
   sector = None
   sector_etf = None
   sector_beta = 0
   
   # Map of sector ETFs
   sector_etf_map = {
      "technology": "XLK",
      "financial": "XLF",
      "health_care": "XLV",
      "consumer_discretionary": "XLY",
      "consumer_staples": "XLP",
      "energy": "XLE",
      "industrial": "XLI",
      "materials": "XLB",
      "utilities": "XLU",
      "real_estate": "XLRE",
      "communication": "XLC"
   }
   
   # Only calculate sector beta for stocks, not ETFs
   if not is_etf:
      # Try to determine the sector from database schemas
      try:
         # Load schema definition
         with open('database_schemas.json', 'r') as f:
            schema_data = json.load(f)
         
         # Find ticker location and sector
         for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            for schema_name, schema_info in schemas.items():
               tables = schema_info.get('tables', {})
               
               for table_name, table_info in tables.items():
                  tickers = table_info.get('tickers', [])
                  
                  if ticker.upper() in [t.upper() for t in tickers]:
                     # Found the ticker, use this sector
                     sector = sector_name
                     break
               if sector: break
            if sector: break
         
         # Map sector name to corresponding ETF
         if sector:
            # Try to match sector name with sector ETF map keys
            matched_sector = None
            for sector_key in sector_etf_map.keys():
               if sector_key in sector.lower():
                  matched_sector = sector_key
                  break
            
            # If found matching sector, calculate sector beta
            if matched_sector:
               sector_etf = sector_etf_map[matched_sector]
               
               # Get the sector ETF data
               sector_etf_data = get_daily_closing_prices(sector_etf)
               
               if sector_etf_data is not None:
                  sector_etf_df = sector_etf_data
                  sector_etf_df['daily_return'] = sector_etf_df['close'].pct_change()
                  sector_etf_df = sector_etf_df.dropna()
                  
                  # Align the dates between stock and sector ETF data
                  merged_sector_data = pd.merge(
                     df[['date', 'daily_return']], 
                     sector_etf_df[['date', 'daily_return']], 
                     on='date', 
                     how='inner',
                     suffixes=('_stock', '_sector')
                  )
                  
                  if not merged_sector_data.empty:
                     # Calculate sector beta as covariance / variance
                     sector_covariance = np.cov(merged_sector_data['daily_return_stock'], merged_sector_data['daily_return_sector'])[0, 1]
                     sector_variance = np.var(merged_sector_data['daily_return_sector'])
                     if sector_variance > 0:
                        sector_beta = sector_covariance / sector_variance
      except Exception as e:
         print(f"Error calculating sector beta: {e}")
   
   # Create base metrics dictionary
   metrics = {
      "sharpe_ratio": float(round(annual_sharpe, 2)),
      "sortino_ratio": float(round(sortino_ratio, 2)),
      "calmar_ratio": float(round(calmar_ratio, 2)),
      "annualized_return": float(round(annual_return, 4)),
      "annualized_volatility": float(round(annual_volatility, 2)),
      "daily_return_volatility": float(round(std_daily_return, 2)),
      "max_drawdown": float(round(max_drawdown, 2)),
      "beta": float(round(beta, 2)),
      "date_range": [df['date'].min().strftime('%Y-%m-%d'), df['date'].max().strftime('%Y-%m-%d')],
      "sector_beta": float(round(sector_beta, 2)),
      "upside_capture": float(round(upside_capture, 2)),
      "downside_capture": float(round(downside_capture, 2)),
      "momentum_6m": float(round(momentum_6m, 4)),
      "momentum_12m": float(round(momentum_12m, 4))
   }
   
   return metrics

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
            
            # First check if data exists from 2015
            check_data_query = f"""
            SELECT COUNT(*) 
            FROM {ticker_location['schema']}.{table_name}
            WHERE date >= '2018-01-01'
            """
            cursor.execute(check_data_query)
            data_count = cursor.fetchone()[0]
            
            # Query table data - from 2015 if data exists, otherwise all data
            if data_count > 0:
               query = f"""
               SELECT *
               FROM {ticker_location['schema']}.{table_name}
               WHERE date >= '2018-01-01'
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

def analyze_fundamentals(ticker):
    """
    Analyze fundamental data for a specific stock using LLM
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        str: Analysis results
    """
    # Get fundamental data - specifically financial_metrics only
    raw_data = get_fundamentals_data(ticker)
    if not raw_data or 'financial_metrics' not in raw_data:
        return f"No fundamental data found for {ticker}"
        
    fundamentals = raw_data['financial_metrics']
    # print(fundamentals)
    
    # Check if fundamentals has data
    if not fundamentals:
        return f"No financial metrics found for {ticker}"
        
    print(f"Found {len(fundamentals)} financial metric records for {ticker}")
    
    # Filter to only include the specific metrics requested
    filtered_data = []
    for item in fundamentals:
        filtered_item = {
            'date': item.get('date'),
            'ticker': ticker.upper(),
            'price_to_earnings_ratio': item.get('price_to_earnings_ratio'),
            'enterprise_value_to_ebitda_ratio': item.get('enterprise_value_to_ebitda_ratio'),
            'net_margin': item.get('net_margin'),
            'revenue_growth': item.get('revenue_growth'),
            'current_ratio': item.get('current_ratio'),
            'debt_to_equity': item.get('debt_to_equity'),
            'free_cash_flow_per_share': item.get('free_cash_flow_per_share'),
            'inventory_turnover': item.get('inventory_turnover'),
        }
        # Only add items that have at least some data
        filtered_data.append(filtered_item)
    

    # Create system prompt
    system_prompt = """
You are a financial analyst specializing in fundamental analysis.
Analyze the provided financial data and provide insights on the company's:
1. Financial health and stability
2. Growth trends
3. Profitability trends
4. Key strengths and weaknesses
5. Give your final overall analysis of the funamental data for the given company

UNDERSTANDING THE METRICS:
- "sharpe_ratio": Risk-adjusted return metric. Higher values indicate better risk-adjusted performance. Values > 1 are generally good.
- "sortino_ratio": Similar to Sharpe but only penalizes downside volatility. Higher values are better.
- "calmar_ratio": Return relative to maximum drawdown. Higher values indicate better return per unit of downside risk.
- "annualized_return": The total return expressed as annual percentage. Higher values represent stronger performance.
- "annualized_volatility": The standard deviation of returns expressed annually. Lower values indicate more stability.
- "daily_return_volatility": Standard deviation of daily returns. Lower values mean more consistent day-to-day performance.
- "max_drawdown": Maximum loss from peak to trough. Closer to zero means smaller worst-case losses.
- "beta": Stock's movement relative to the market. >1 means more volatile than market, <1 means less volatile.
- "sector_beta": Similar to beta but measured against the stock's sector rather than overall market.
- "upside_capture": Measures how much a stock gains relative to the market in up periods. >1 means outperforming in bull markets.
- "downside_capture": Measures losses relative to market in down periods. <1 is better (smaller losses than market).
- "momentum_6m": 6-month cumulative return. Higher values indicate stronger recent performance trend.
- "momentum_12m": 12-month cumulative return. Higher values indicate stronger medium-term performance trend.

IMPORTANT:
- Write a brief response with the most important information, be precise and informative.
- Do not include any '#' or '*' in your response.
- If there is no data or something you do not know, say you dont know.
"""

    # Initialize messages with filtered financial data directly included
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze the fundamental data for {ticker.upper()}. Here is the financial data:\n{json.dumps(filtered_data)}"}
    ]
    
    # Make a single API call with the data already included
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1000
    )


    return response.choices[0].message.content

def get_news_sentiment(query):
    """
    Get news sentiment for a particular stock.
    
    Args:
        query (str): A detailed query to retrieve recent news about a stock (this should be a detailed query)
        
    Returns:
        str: News sentiment results
    """
    # Set up system and user prompts
    system_prompt = "You are a financial analyst. Analyze news sentiment about stocks objectively."
    user_prompt = f"Analyze the recent news sentiment for: {query}. Provide a summary of the sentiment (positive, negative, or neutral) with supporting evidence from recent articles. The date is {datetime.now().strftime('%Y-%m-%d')}, do not take news into account that is more than 2 weeks old. This is for a stock outlook to see if I should recomend to buy or not. Make sure to look at analyst ratings."
    
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {   
            "role": "user",
            "content": user_prompt
        },
    ]

    # Initialize client with Perplexity API - use a different variable name to avoid overwriting global client
    perplexity_client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # Chat completion without streaming
        response = perplexity_client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=messages
        )
        
        # Get the response content
        result = response.choices[0].message.content
        return result
                
    except Exception as e:
        error_message = f"Error retrieving news sentiment: {str(e)}"
        print(error_message)
        return error_message

def extract_asset_classes(json_data):
    """
    Extract asset classes from portfolio JSON data.
    
    Args:
        json_data (str): JSON string containing portfolio data
        
    Returns:
        list: List of asset class names with 'cash' filtered out
    """
    # Parse the JSON string
    import json
    data = json_data
    
    # Extract asset classes using list comprehension
    asset_classes = [item["asset_class"] for item in data["portfolio"]]
    
    # Filter out 'cash' from the list
    asset_classes = [asset for asset in asset_classes if asset.lower() != 'cash']
    
    return asset_classes

def get_stock_tickers(filter_value):
    """
    Retrieve stock tickers from database_schemas.json filtered by a value.
    The function automatically determines if the filter value is a sector, industry, or subindustry.
    
    Args:
        filter_value (str, optional): Value to filter on. If None, returns all tickers.
    
    Returns:
        dict: Dictionary with filter_value as key and list of matching stock tickers as value
    """

    with open('database_schemas.json', 'r') as f:
        schema_data = json.load(f)
    
    # List to store all matching tickers
    matching_tickers = []
    
    # If no filter is provided, return all tickers
    if filter_value is None:
        for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            for schema_name, schema_info in schemas.items():
                tables = schema_info.get('tables', {})
                
                for table_name, table_info in tables.items():
                    tickers = table_info.get('tickers', [])
                    matching_tickers.extend(tickers)
                    
        return {"all": matching_tickers}
    
    # Check if filter_value is a sector
    if filter_value in schema_data:
        # Filter by sector
        sector_info = schema_data[filter_value]
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
                if schema_name == filter_value:
                    tables = schema_info.get('tables', {})
                    for table_name, table_info in tables.items():
                        tickers = table_info.get('tickers', [])
                        matching_tickers.extend(tickers)
                
                # Check for subindustry match in table names
                tables = schema_info.get('tables', {})
                for table_name, table_info in tables.items():
                    if table_name == filter_value:
                        tickers = table_info.get('tickers', [])
                        matching_tickers.extend(tickers)
    
    # Remove duplicates and sort list
    sorted_tickers = sorted(list(set(matching_tickers)))
    
    # Return dictionary with filter_value as key and ticker list as value
    return {filter_value: sorted_tickers}

def filter_stocks(ticker_input):
    """
    Filter stocks based on quantitative metrics using z-scores to identify highest potential performers.
    
    Args:
        ticker_input: Either a dictionary {filter_value: [tickers]} or a list of tickers
        
    Returns:
        If input is a dictionary: Dictionary with filter_value as key and list of top tickers as value
        If input is a list: List of top tickers
    """
    result_dict = {}
    
    # Check if input is a list or dictionary and handle accordingly
    if isinstance(ticker_input, list):
        # If input is a list, process it directly
        ticker_list = ticker_input
        all_metrics = {}
        
        # Step 1: Calculate metrics for all tickers
        for ticker in ticker_list:
            metrics = calculate_stock_metrics(ticker)
            all_metrics[ticker] = metrics
        
        # Step 2: Convert metrics to DataFrame for z-score calculation
        metrics_data = []
        for ticker, metrics in all_metrics.items():
            metrics_row = {'Ticker': ticker}
            metrics_row.update(metrics)
            metrics_data.append(metrics_row)
        
        df = pd.DataFrame(metrics_data)
        
        # Define metrics based on whether higher or lower values are better
        higher_is_better = [
            'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'annualized_return',
            'upside_capture', 'momentum_6m', 'momentum_12m'
        ]
        
        lower_is_better = [
            'annualized_volatility', 'daily_return_volatility', 'max_drawdown', 'beta',
            'sector_beta', 'downside_capture'
        ]
        
        # Calculate z-scores for each metric
        z_scores = df.copy()
        for col in higher_is_better + lower_is_better:
            if col in df.columns and df[col].std() != 0:
                z_scores[col] = (df[col] - df[col].mean()) / df[col].std()
            else:
                # Skip or set to 0 if column is missing or has no variation
                z_scores[col] = 0
        
        # Adjust z-scores for metrics where lower is better
        for col in lower_is_better:
            if col in z_scores.columns:
                z_scores[col] = -z_scores[col]
        
        # Calculate composite score by summing adjusted z-scores
        metric_columns = [col for col in higher_is_better + lower_is_better if col in z_scores.columns]
        z_scores['composite_score'] = z_scores[metric_columns].sum(axis=1)
        
        # Rank stocks by composite score in descending order
        ranked_df = z_scores.sort_values(by='composite_score', ascending=False)
        
        # Get the top 10 tickers (or all tickers if less than 10 are available)
        max_stocks = 10
        available_stocks = min(max_stocks, len(ranked_df))
        filtered_tickers = ranked_df.head(available_stocks)['Ticker'].tolist()
        
        # Return list directly for list input
        return filtered_tickers
        
    else:
        # Process each filter_value and its tickers for dictionary input
        for filter_value, ticker_list in ticker_input.items():
            all_metrics = {}
            
            # Step 1: Calculate metrics for all tickers
            for ticker in ticker_list:
                metrics = calculate_stock_metrics(ticker)
                all_metrics[ticker] = metrics
            
            # Step 2: Convert metrics to DataFrame for z-score calculation
            metrics_data = []
            for ticker, metrics in all_metrics.items():
                metrics_row = {'Ticker': ticker}
                metrics_row.update(metrics)
                metrics_data.append(metrics_row)
            
            df = pd.DataFrame(metrics_data)
            
            # Define metrics based on whether higher or lower values are better
            higher_is_better = [
                'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'annualized_return',
                'upside_capture', 'momentum_6m', 'momentum_12m'
            ]
            
            lower_is_better = [
                'annualized_volatility', 'daily_return_volatility', 'max_drawdown', 'beta',
                'sector_beta', 'downside_capture'
            ]
            
            # Calculate z-scores for each metric
            z_scores = df.copy()
            for col in higher_is_better + lower_is_better:
                if col in df.columns and df[col].std() != 0:
                    z_scores[col] = (df[col] - df[col].mean()) / df[col].std()
                else:
                    # Skip or set to 0 if column is missing or has no variation
                    z_scores[col] = 0
            
            # Adjust z-scores for metrics where lower is better
            for col in lower_is_better:
                if col in z_scores.columns:
                    z_scores[col] = -z_scores[col]
            
            # Calculate composite score by summing adjusted z-scores
            metric_columns = [col for col in higher_is_better + lower_is_better if col in z_scores.columns]
            z_scores['composite_score'] = z_scores[metric_columns].sum(axis=1)
            
            # Rank stocks by composite score in descending order
            ranked_df = z_scores.sort_values(by='composite_score', ascending=False)
            
            # Get the top 10 tickers (or all tickers if less than 10 are available)
            max_stocks = 10
            available_stocks = min(max_stocks, len(ranked_df))
            filtered_tickers = ranked_df.head(available_stocks)['Ticker'].tolist()
            
            # Add the filtered tickers to the result dictionary
            result_dict[filter_value] = filtered_tickers
        
        return result_dict

def run_portfolio_manager(tickers=None):
   """
   Run the portfolio manager to analyze stocks and make recommendations.
   
   Args:
      tickers (dict or list, optional): Dictionary with industry as key and list of ticker symbols as value,
                                       or a list of ticker symbols to analyze.
                                       If None, will retrieve all tickers.
      
   This function enforces a strict sequential workflow for consistent analysis:
   1. Gather all tickers
   2. For each ticker, analyze in sequence: metrics → fundamentals → sentiment
   3. After all tickers are analyzed, select the best stocks
   """
   # Get tickers if not provided
   if tickers is None:
      print("Retrieving all stock tickers...")
      tickers = get_stock_tickers(None)
   
   etf_categories = [
      "alternative_etfs", 
      "commodity_etfs", 
      "equity_etfs", 
      "fixed_income_etfs",
      "private_equity_exposure_etfs",
      "business_development_companies",
      "closed_end_funds_that_hold_private_equity_late_sta",
      "equity_selection_hedge_fund_holding_clones",
      "hedge_funds",
      "ipo_focused_etfs_late_stage_tech_pre_ipo_th",
      "softs",
      "broad_commodity_etfs",
      "energy_focused_etfs",
      "grains",
      "industrial_metals",
      "livestock",
      "precious_metals_etfs",
      "single_country_and_regional_etfs_in_emerging_marke",
      "sector_specific_etfs",
      "barra_styleetfs",
      "broad_us_market",
      "broad_based_emerging_market_equity_etfs",
      "factor_style_and_specialized_em_etfs",
      "global_international_etfs",
      "convertible_bonds",
      "high_yield_junk_bond_etfs",
      "investment_grade_corporate_bond_etfs",
      "treasury_and_inflation_bond_etfs"
   ]
   
   # Store all ticker analysis data
   all_analysis_data = {}
   
   # Handle dictionary input format
   if isinstance(tickers, dict):
      # Process by industry
      for industry, ticker_list in tickers.items():
         # Check if 'etfs' appears in the industry name
         if industry in etf_categories:
            print("It's an etf")
         
            print(f"\nBeginning analysis of {len(ticker_list)} tickers in {industry}...")
            
            # Process each ticker sequentially
            for ticker in ticker_list:
               print(f"\nAnalyzing ticker: {ticker}")
               ticker_data = {}
               
               # Step 1: Calculate stock metrics
               print(f"Calculating metrics for {ticker}...")
               metrics = calculate_stock_metrics(ticker)
               ticker_data["metrics"] = metrics
               
               # Skip fundamentals for ETFs and add a placeholder
               ticker_data["fundamentals"] = "ETF fundamental data not analyzed"
               
               # Step 2: Get news sentiment
               print(f"Getting news sentiment for {ticker}...")
               query = f"{ticker} etf recent performance analyst ratings news institutional ownership price targets forecasts"
               sentiment = get_news_sentiment(query)
               ticker_data["sentiment"] = sentiment
               
               # Store complete analysis for this ticker
               all_analysis_data[ticker] = ticker_data
         
         else:
            print(f"\nBeginning analysis of {len(ticker_list)} tickers in {industry}...")
            
            # Process each ticker sequentially
            for ticker in ticker_list:
               print(f"\nAnalyzing ticker: {ticker}")
               ticker_data = {}
               
               # Step 1: Calculate stock metrics
               print(f"Calculating metrics for {ticker}...")
               metrics = calculate_stock_metrics(ticker)
               ticker_data["metrics"] = metrics
               
               # Step 2: Analyze fundamentals
               print(f"Analyzing fundamentals for {ticker}...")
               fundamentals = analyze_fundamentals(ticker)
               ticker_data["fundamentals"] = fundamentals
               
               # Step 3: Get news sentiment
               print(f"Getting news sentiment for {ticker}...")
               query = f"{ticker} stock recent performance analyst ratings news institutional ownership price targets earnings forecasts"
               sentiment = get_news_sentiment(query)
               ticker_data["sentiment"] = sentiment
               
               # Store complete analysis for this ticker
               all_analysis_data[ticker] = ticker_data
   
   # Handle list input format (backward compatibility)
   else:
      print(f"Beginning analysis of {len(tickers)} tickers...")
      
      # Process each ticker sequentially
      for ticker in tickers:
         print(f"\nAnalyzing ticker: {ticker}")
         ticker_data = {}
         
         # Step 1: Calculate stock metrics
         print(f"Calculating metrics for {ticker}...")
         metrics = calculate_stock_metrics(ticker)
         ticker_data["metrics"] = metrics
         
         # Step 2: Analyze fundamentals
         print(f"Analyzing fundamentals for {ticker}...")
         fundamentals = analyze_fundamentals(ticker)
         ticker_data["fundamentals"] = fundamentals
         
         # Step 3: Get news sentiment
         print(f"Getting news sentiment for {ticker}...")
         query = f"{ticker} stock recent performance analyst ratings news institutional ownership price targets earnings forecasts"
         sentiment = get_news_sentiment(query)
         ticker_data["sentiment"] = sentiment
         
         # Store complete analysis for this ticker
         all_analysis_data[ticker] = ticker_data
   
   print(f"\nCompleted analysis of all tickers. Preparing final recommendations...")
   
   # Initialize conversation with system instructions for the final recommendation
   messages = [
      {
         "role": "system", 
         "content": f"""
<think>

You are a very skilled portfolio manager with 30 years of experience. 

TASK:
You will receive the complete analysis data for {len(all_analysis_data)} stocks. Your job is to identify the top 2-3 stocks with the best overall performance.

ANALYSIS APPROACH:
- Review ALL the provided data carefully
- Evaluate each stock based on a combination of:
1. Performance metrics (sharpe ratio, sortino ratio, etc.)
2. Fundamental data (when available)
3. News sentiment
- Choose the 2-3 stocks that you believe have the best investment potential

OUTPUT FORMAT:
Return your recommendations in this JSON format:
{{
"total_stocks_analyzed": {len(all_analysis_data)},
"recommendations": [
   {{
   "ticker": [string],
   "justification": [string],
   "fundamental_overview": [string],
   "sentiment": [string],
   "sharpe_ratio": [float],
   "sortino_ratio": [float],
   "calmar_ratio": [float],
   "annualized_return": [float],
   "annualized_volatility": [float],
   "daily_return_volatility": [float],
   "max_drawdown": [float],
   "beta": [float],
   "sector_beta": [float],
   "upside_capture": [float],
   "downside_capture": [float], 
   "momentum_6m": [float],
   "momentum_12m": [float]
   }}
]
}}

UNDERSTANDING THE METRICS:
- "sharpe_ratio": Risk-adjusted return metric. Higher values indicate better risk-adjusted performance. Values > 1 are generally good.
- "sortino_ratio": Similar to Sharpe but only penalizes downside volatility. Higher values are better.
- "calmar_ratio": Return relative to maximum drawdown. Higher values indicate better return per unit of downside risk.
- "annualized_return": The total return expressed as annual percentage. Higher values represent stronger performance.
- "annualized_volatility": The standard deviation of returns expressed annually. Lower values indicate more stability.
- "daily_return_volatility": Standard deviation of daily returns. Lower values mean more consistent day-to-day performance.
- "max_drawdown": Maximum loss from peak to trough. Closer to zero means smaller worst-case losses.
- "beta": Stock's movement relative to the market. >1 means more volatile than market, <1 means less volatile.
- "sector_beta": Similar to beta but measured against the stock's sector rather than the S&P 500.
- "upside_capture": Measures how much a stock gains relative to the market in up periods. >1 means outperforming in bull markets.
- "downside_capture": Measures losses relative to market in down periods. <1 is better (smaller losses than market).
- "momentum_6m": 6-month cumulative return. Higher values indicate stronger recent performance trend.
- "momentum_12m": 12-month cumulative return. Higher values indicate stronger medium-term performance trend.

IMPORTANT:
- Base your recommendations on the data provided - don't hallucinate additional information
- If there is missing information for certain stocks, you may exclude them from consideration
- For ETFs, fundamental data will be marked as "ETF fundamental data not analyzed"
- Provide a concise but thorough justification for each recommendation
         """
      },
      {
         "role": "user", 
         "content": f"Here is the complete analysis data for {len(all_analysis_data)} tickers: {json.dumps(all_analysis_data)}\n\nPlease analyze this data and provide your top 2-3 stock recommendations."
      }
   ]

   # Get final recommendations from the model
   response = client.chat.completions.create(
      model=model,
      messages=messages
   )
   
   # Extract and return the final recommendations
   recommendations = response.choices[0].message.content
   print("Analysis complete!")
   return recommendations


final = {}

asset_classes = extract_asset_classes(portfolio_data)
print(asset_classes)

for asset in asset_classes:
   x = get_stock_tickers(asset)
   print(x)
   
   filtered_tickers = filter_stocks(x)
   print(filtered_tickers)

   result_json = run_portfolio_manager(filtered_tickers)
   print(result_json)  # Keep printing the raw JSON output if needed for debugging

   try:
       # Find the start and end of the actual JSON content within the string
       start_index = result_json.find('{')
       end_index = result_json.rfind('}')
       
       if start_index != -1 and end_index != -1:
           cleaned_json_str = result_json[start_index : end_index + 1]
           
           # Parse the cleaned JSON string into a dictionary
           result_data = json.loads(cleaned_json_str)
           
           # Iterate through recommendations and populate the final dictionary
           if 'recommendations' in result_data:
               for recommendation in result_data['recommendations']:
                   ticker = recommendation.get('ticker')
                   justification = recommendation.get('justification')
                   if ticker: # Ensure ticker is not None or empty
                       final[ticker] = justification
           else:
               print("No 'recommendations' key found in the result.")
       else:
           print("Could not find valid JSON structure ('{' and '}') in the result string.")

   except json.JSONDecodeError as e:
       print(f"Error decoding JSON: {e}")
   except Exception as e:
       print(f"An error occurred while processing recommendations: {e}")

print("Final recommendations dictionary:")
print(final)