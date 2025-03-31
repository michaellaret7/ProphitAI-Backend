from agents import Agent, Runner, function_tool, FileSearchTool, WebSearchTool
import asyncio
import re
import json
from openai import OpenAI
import psycopg2
from decimal import Decimal
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")

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

@function_tool
def calculate_stock_metrics(ticker: str):
   """
   Calculate the Sharpe ratio and other risk-adjusted performance metrics for a stock.
   
   This function retrieves historical price data for a given stock ticker and calculates
   several key performance metrics used in portfolio analysis and risk assessment:
   
   - Sharpe Ratio: Measures risk-adjusted return (excess return per unit of risk)
   - Sortino Ratio: Similar to Sharpe but only penalizes downside volatility
   - Calmar Ratio: Measures return relative to maximum drawdown
   - Annualized Return: Total return expressed on an annual basis
   - Volatility: Standard deviation of returns (annualized and daily)
   - Maximum Drawdown: Largest peak-to-trough decline during the period
   
   The calculations use a risk-free rate of 3% and annualization factor of 252 trading days.
   Historical data covers the most recent 3 years by default.
   
   Args:
       ticker (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT')
   
   Returns:
       dict: Dictionary containing calculated financial metrics:
           - sharpe_ratio (float): Annualized Sharpe ratio (higher is better)
           - sortino_ratio (float): Annualized Sortino ratio (higher is better)
           - calmar_ratio (float): Calmar ratio (return relative to max drawdown)
           - annualized_return (float): Return expressed on annual basis
           - annualized_volatility (float): Volatility expressed on annual basis
           - daily_return_volatility (float): Standard deviation of daily returns
           - max_drawdown (float): Maximum peak-to-trough decline (always negative)
           - data_points (int): Number of trading days in the analysis
           - date_range (list): Start and end dates of the analyzed period [start_date, end_date]
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
   print(f"Ticker: {ticker}")
   
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

@function_tool
def get_news_sentiment(query: str):
   """
   Args: A detailed query into a search engine to retrieve recent news about a stock.
   """
   print(query)
   return query


def main_agent():
    # The agent should now be able to access the API key from the environment variable
    agent = Agent(
        name="Portfolio Manager",
        instructions=f"""
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
        tools=[
            calculate_stock_metrics,
            FileSearchTool(vector_store_ids=["vs_67e9cd40d06c819191c42f9de2cde622"]),
            get_news_sentiment
        ],
        model=OPENAI_MODEL
    )


    
    result = Runner.run_sync(agent, input="Analyze the stocks and make your recommendations", max_turns=100)
    print(result.final_output)
    return True

def run_multi_agent():
    # First agent - Portfolio Manager
    portfolio_manager = Agent(
        name="Portfolio Manager",
        instructions="""
You are a portfolio manager, you must pick the best 4 stocks to build a portfolio.
Use the calculate_stock_metrics tool to analyze the performance of the stocks.
Print the results of the analysis.
ayro, cenn, ecda, evtv, f, ggr, gm, hog, lcid, li, gpro, grmn, hbb, hov, flxs, dfh, crct, ccs, flxs, dfh, crct, ccs,
""",
        tools=[calculate_stock_metrics],
        model=OPENAI_MODEL
    )
    
    # Second agent - Risk Analyst
    risk_analyst = Agent(
        name="Risk Analyst",
        instructions="""
You are a risk analyst who evaluates portfolio suggestions.
Examine the stocks suggested by the portfolio manager and provide risk assessment.
Focus on drawdowns, volatility, and correlation risks.
""",
        tools=[calculate_stock_metrics],
        model=OPENAI_MODEL
    )
    
    # Agent interaction function
    def have_conversation():
        # Get user input for a specific question
        stock_query = input("🚀 What stocks would you like analyzed? ")
        
        # First agent analyzes stocks
        pm_result = Runner.run_sync(portfolio_manager, "Analyze these stocks and suggest a portfolio")
        print(f"\n📊 Portfolio Manager: {pm_result.final_output}\n")
        
        # Second agent analyzes the first agent's response
        ra_result = Runner.run_sync(risk_analyst, 
            f"Evaluate this portfolio suggestion: {pm_result.final_output}")
        print(f"\n⚠️ Risk Analyst: {ra_result.final_output}\n")
        
        # You could continue the conversation with more rounds
        return True
    
    # Run the conversation
    have_conversation()

main_agent()
# run_multi_agent()
