import os
import json
import pandas as pd
import numpy as np
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from openai import OpenAI
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL")
client = OpenAI(api_key=OPENAI_API_KEY)

def get_daily_closing_prices(ticker, years=3, db_config=None):
   """
   Retrieve daily closing prices (last bar of each day) for a given stock
   """
   # Database configuration
   if db_config is None:
      db_config = {
         "host": "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com",
         "user": "postgres",
         "password": "ml1710402!",
         "port": "5432"
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
               
               if ticker_upper in tickers:
                  ticker_location = {
                     "database": f"{database}_prices",
                     "schema": f"{schema_name}_prices",
                     "ticker": ticker_upper
                  }
                  break
         if ticker_location: break
      if ticker_location: break
   
   if not ticker_location:
      print(f"Ticker {ticker_upper} not found")
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
      print(f"Error retrieving stock data: {e}")
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
   
   # Convert risk-free rate to daily
   daily_risk_free_rate = (1 + risk_free_rate) ** (1/annualization_factor) - 1
   
   # Calculate daily Sharpe ratio
   daily_sharpe = (mean_daily_return - daily_risk_free_rate) / std_daily_return
   
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
   
   return {
      "sharpe_ratio": float(round(annual_sharpe, 2)),
      "sortino_ratio": float(round(sortino_ratio, 2)),
      "calmar_ratio": float(round(calmar_ratio, 2)),
      "annualized_return": float(round(annual_return, 2)),
      "annualized_volatility": float(round(annual_volatility, 2)),
      "daily_return_volatility": float(round(std_daily_return, 2)),
      "max_drawdown": float(round(max_drawdown, 2)),
      "data_points": len(daily_returns),
      "date_range": [df['date'].min().strftime('%Y-%m-%d'), df['date'].max().strftime('%Y-%m-%d')]
   }

def get_fundamentals_data(ticker, db_config=None):
   """
   Retrieve all fundamental data for a given stock across different tables
   (balance sheets, cash flow statements, financial metrics, etc.)
   """
   # Database configuration
   if db_config is None:
      db_config = {
         "host": "demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com",
         "user": "postgres",
         "password": "ml1710402!",
         "port": "5432"
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
                  ticker_location = {
                     "database": f"{database}_fundamentals",
                     "schema": f"{schema_name}",
                     "ticker": ticker_upper
                  }
                  break
         if ticker_location: break
      if ticker_location: break
   
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
               
            # Query table data
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

# Helper function to create a file search assistant
def get_stock_tickers():
    """
    Retrieve all available stock tickers from the vector store.
    
    Returns:
        list: List of available stock tickers
    """
    # Create an assistant with file search capability
    assistant = client.beta.assistants.create(
        name="Stock Ticker Finder",
        instructions="You are an assistant that retrives stock tickers from the database.",
        model=OPENAI_MODEL,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": ["vs_67e9cd40d06c819191c42f9de2cde622"]}}
    )
    
    # Create a thread for file search
    thread = client.beta.threads.create()
    
    # Add a message asking for stock tickers
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="List all available stock tickers in the dataset"
    )
    
    # Run the assistant with file search tool
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    
    # Wait for completion
    while run.status not in ["completed", "failed"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    
    if run.status == "failed":
        return ["Error retrieving tickers"]
    
    # Get the file search results
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    for message in messages.data:
        if message.role == "assistant":
            # Extract ticker list from the assistant's response
            # This assumes the response is formatted as a list of tickers
            content = message.content[0].text.value
            # Simple parsing - this may need to be adjusted based on actual response format
            tickers = [ticker.strip() for ticker in content.replace("[", "").replace("]", "").split(",")]
            return tickers
    
    return "something went wrong"  # Fallback to sample list

def get_news_sentiment(query):
    """
    Get news sentiment for a particular stock.
    
    Args:
        query (str): A detailed query to retrieve recent news about a stock
        
    Returns:
        str: News sentiment results
    """
    # Get Perplexity API key from environment variables
    Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
    
    # Set up system and user prompts
    system_prompt = "You are a financial analyst. Analyze news sentiment about stocks objectively."
    user_prompt = f"Analyze the recent news sentiment for: {query}. Provide a summary of the sentiment (positive, negative, or neutral) with supporting evidence from recent articles. The date is March 30th, 2025, do not take news into account that is more than 2 weeks old. This is for a stock outlook to see if I should recomend to buy or not. Make sure to look at analyst ratings."
    
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

    # Initialize client with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # Chat completion without streaming
        response = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=messages
        )
        
        # Get the response content
        result = response.choices[0].message.content
        
        # Print the output
        print(result)
        
        return result
                
    except Exception as e:
        error_message = f"Error retrieving news sentiment: {str(e)}"
        print(error_message)
        return error_message

# Define the function schemas for OpenAI function calling
available_functions = {
    "get_stock_tickers": get_stock_tickers,
    "calculate_stock_metrics": calculate_stock_metrics,
    "get_news_sentiment": get_news_sentiment
}

# Function schema definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_tickers",
            "description": "Retrieve all available stock tickers from the system",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_stock_metrics",
            "description": "Calculate performance metrics for a specific stock ticker",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol (e.g., 'AAPL', 'MSFT')"
                    }
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_sentiment",
            "description": "Get news sentiment for a specific stock or query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A detailed query to retrieve recent news about a stock"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def run_portfolio_manager():
    """
    Run the portfolio manager to analyze stocks and make recommendations.
    
    This function uses OpenAI function calling to orchestrate the analysis process.
    """
    # Initialize conversation with system instructions
    messages = [
        {
            "role": "system", 
            "content": """
You are a very skilled portfolio manager at JP Morgan. 
INSTRUCTIONS - FOLLOW THESE STEPS IN ORDER:
1. Use the file search tool to retrieve ALL of the stock tickers that you can choose from.
2. Create a comprehensive list of ALL tickers found in the vector store.
3. Use the calculate_stock_metrics tool to calculate the performance of EVERY SINGLE stock in your list.
   - You MUST process all stocks without exception
   - Keep track of how many stocks you've analyzed and ensure it matches the total count
4. After analyzing ALL stocks, identify the 10 stocks with the best performance metrics.
   - Rank them based on Sharpe ratio, Sortino ratio, and other key metrics
   - Create a clear table showing the top performers and their metrics
5. Use the get_news_sentiment tool to get the news sentiment for EACH of these 10 stocks.
   - Build a detailed query into a search engine to retrieve recent news about the stocks.
   - For example: "Latest financial performance, analyst ratings, and major news events for [TICKER] in the past two weeks, including earnings reports, regulatory changes, and market sentiment"
   - The date is March 30th, 2025, do not take news into account that is more than 2 weeks old.
6. Pick the best 3 stocks to build a portfolio based on BOTH metrics and sentiment.
7. Return the results of the analysis in this structured format:
   - Total stocks analyzed: [number]
   - Top 10 performing stocks with their key metrics
   - News sentiment summary for each top stock
   - Final 3 recommendations with detailed justification

IMPORTANT:
- You MUST analyze ALL stocks available in the vector store - expected to be approximately 49 stocks.
- The decision of which stocks to pick must be made using BOTH the news sentiment and the performance metrics.
- No hallucinations, if there is missing information, say you don't know.
- DO NOT get stuck in analysis loops. Complete the task efficiently.
- If you find yourself not analyzing all stocks, STOP and restart the process to ensure complete coverage.
        """,
        },
        {
            "role": "user", 
            "content": "Analyze the stocks and make your recommendations"
        }
    ]

    # Process will continue until we get a final message without a function call
    while True:
        # Get model response
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=tools,
            temperature=0.75
        )
        
        # Extract the response message
        response_message = response.choices[0].message
        
        # Add the response to the messages
        messages.append(response_message)
        
        # Check if the model wants to call a function
        if response_message.tool_calls:
            # Process each function call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Ensure the function exists
                if function_name in available_functions:
                    function_to_call = available_functions[function_name]
                    
                    # Call the function
                    print(f"Calling function: {function_name} with args: {function_args}")
                    if function_name == "calculate_stock_metrics":
                        function_response = function_to_call(function_args.get("ticker"))
                    elif function_name == "get_news_sentiment":
                        function_response = function_to_call(function_args.get("query"))
                    else:  # get_stock_tickers has no args
                        function_response = function_to_call()
                    
                    # Add the function response to the messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                else:
                    # Handle case where function doesn't exist
                    print(f"Error: Function {function_name} does not exist")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"error": f"Function {function_name} does not exist"})
                    })
        else:
            # No function call, we're done
            print("Analysis complete:")
            print(response_message.content)
            return response_message.content


