import os
import json
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from openai import OpenAI

# Import from utils package
from src.utils.caching import cache_result
from src.utils.file_utils import load_schema_data

# Import from our module
from src.phaseTwo.data_retrieval import get_daily_closing_prices, get_fundamentals_data

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load environment variables
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_model = "deepseek-reasoner"

openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_model = os.environ.get("OPENAI_MODEL")

grok_api_key = os.environ.get("GROK_API_KEY")
grok_model = os.environ.get("GROK_MODEL")

model = deepseek_model

# Instead of initializing at module level, create a function
def get_openai_client():
    """Get OpenAI client with appropriate configuration based on selected model"""
    if model == openai_model:
        return OpenAI(api_key=openai_api_key)
    elif model == deepseek_model:
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    elif model == grok_model:
        return OpenAI(api_key=grok_api_key, base_url="https://api.grok.com")
    else:
        raise ValueError(f"Unsupported model: {model}")

@cache_result
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
         "momentum_12m": 0,
         "average_daily_volume": 0
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
   
   # Calculate Average Daily Volume
   average_daily_volume = df['volume'].mean() if 'volume' in df and not df['volume'].empty else 0
   
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
         schema_data = load_schema_data()
         
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
      "momentum_12m": float(round(momentum_12m, 4)),
      "average_daily_volume": int(round(average_daily_volume))
   }
   
   return metrics

@cache_result
def generate_fundamental_analysis_report(ticker):
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
        print(f"DEBUG: No fundamental data found for {ticker}")
        return f"No fundamental data found for {ticker}"
        
    fundamentals = raw_data['financial_metrics']
    
    # Debug: Print raw fundamentals data structure
    print(f"DEBUG: Raw fundamentals data for {ticker}:")
    if fundamentals and len(fundamentals) > 0:
        print(f"  First record type: {type(fundamentals[0])}")
        print(f"  Number of records: {len(fundamentals)}")
        if len(fundamentals) > 0:
            # Print keys from first record
            print(f"  Keys in first record: {list(fundamentals[0].keys())}")
            # Print a sample of values to check for problematic data
            print(f"  Sample values from first record:")
            for key, value in list(fundamentals[0].items())[:5]:  # Show first 5 items
                print(f"    {key}: {value} (type: {type(value)})")
    else:
        print("  Empty fundamentals data")
    
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
    
    # Debug: Print filtered data structure
    print(f"DEBUG: Filtered data for {ticker}:")
    if filtered_data and len(filtered_data) > 0:
        print(f"  First filtered record: {filtered_data[0]}")
    else:
        print("  Empty filtered data")

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

    try:
        # Sanitize data by converting non-serializable objects and removing problematic values
        sanitized_data = []
        for item in filtered_data:
            sanitized_item = {}
            for key, value in item.items():
                # Handle date objects
                if key == 'date' and isinstance(value, str):
                    # Ensure the date is in a valid format
                    sanitized_item[key] = value
                # Handle None, NaN, Inf values
                elif value is None:
                    sanitized_item[key] = None
                elif isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                    sanitized_item[key] = None
                else:
                    # Convert all other values to simple types
                    try:
                        # Try to convert to simpler types if needed
                        if isinstance(value, (int, float, str, bool)):
                            sanitized_item[key] = value
                        else:
                            sanitized_item[key] = str(value)
                    except:
                        # If conversion fails, just use None
                        sanitized_item[key] = None
            
            sanitized_data.append(sanitized_item)
        
        # Debug output - inspect the data before trying to encode
        print(f"DEBUG: Sanitized data for {ticker}:")
        if sanitized_data and len(sanitized_data) > 0:
            print(f"  First sanitized record: {sanitized_data[0]}")
        else:
            print("  Empty sanitized data")
        
        print(f"Preparing to encode data for {ticker} ({len(sanitized_data)} records)")
        
        # Use the debug function to find and fix problems
        success, json_result = debug_json_encoding(sanitized_data, ticker)
        
        if success:
            financial_data_json = json_result
            print(f"Successfully encoded JSON data for {ticker} - length: {len(financial_data_json)}")
            if len(financial_data_json) < 1000:  # Only print if it's not too large
                print(f"DEBUG: JSON data: {financial_data_json[:500]}...")
        else:
            # Fall back to a simplified approach if debug function fails
            print(f"Using simplified data for {ticker}")
            # Create a very simple list with only numbers and strings
            simple_data = []
            for item in sanitized_data:
                simple_item = {}
                for key, value in item.items():
                    if isinstance(value, (int, float)) and not (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
                        simple_item[key] = value
                    elif isinstance(value, str):
                        simple_item[key] = value
                    else:
                        simple_item[key] = None
                simple_data.append(simple_item)
            
            financial_data_json = json.dumps(simple_data)
        
        # Create messages with the sanitized data
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze the fundamental data for {ticker.upper()}. Here is the financial data:\n{financial_data_json}"}
        ]
        
        # Initialize client only when needed
        client = get_openai_client()
        
        # Make a single API call with the data already included
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1500,
            temperature=1.0
        )

        # Return the text content directly without any parsing
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in fundamental analysis for {ticker}: {str(e)}")
        # Try with a simpler approach - convert to string directly
        try:
            print(f"Attempting fallback with str() for {ticker}")
            simple_data = str(filtered_data)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze the fundamental data for {ticker.upper()}. Here is the financial data (in string format):\n{simple_data}"}
            ]
            
            # Initialize client only when needed
            client = get_openai_client()
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=1.0
            )
            
            return response.choices[0].message.content
        except Exception as e2:
            print(f"Fallback also failed for {ticker}: {e2}")
            return f"Error analyzing fundamental data for {ticker}: {str(e)}" 

def debug_json_encoding(data, ticker):
    """
    Debug function to identify which fields are causing JSON encoding issues.
    
    Args:
        data (list): List of dictionaries to encode
        ticker (str): Ticker symbol for logging
        
    Returns:
        tuple: (success_flag, error_message)
    """
    print(f"DEBUG: Testing JSON encoding for {ticker} item by item")
    
    # First try individual records
    for i, record in enumerate(data):
        try:
            json.dumps(record)
        except Exception as e:
            print(f"  Failed to encode record {i}: {e}")
            
            # Try each field individually
            for key, value in record.items():
                try:
                    json.dumps({key: value})
                except Exception as e:
                    print(f"    Problem field: '{key}' with value '{value}' (type: {type(value)}): {e}")
                    
                    # Try to fix this problematic field
                    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                        record[key] = None
                        print(f"      Fixed by replacing with None")
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        record[key] = str(value)
                        print(f"      Fixed by converting to string: '{record[key]}'")
                    else:
                        record[key] = None
                        print(f"      Fixed by replacing with None")
    
    # Try with fixed data
    try:
        json_str = json.dumps(data)
        print(f"  Final JSON encoding successful: {len(json_str)} bytes")
        return True, json_str
    except Exception as e:
        print(f"  Final JSON encoding still failed: {e}")
        return False, str(e)


