import os
import json
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from openai import OpenAI
from src.utils.caching import cache_result
from src.utils.file_utils import load_schema_data
from src.portfolio_optimization.phase_two.data_retrieval import get_daily_closing_prices

daily_volume_threshold = 10000

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

def calculate_and_filter_metrics(ticker_list):
    """Calculate metrics for tickers and filter out those with insufficient data."""
    all_metrics = {}
    for ticker in ticker_list:
        metrics = calculate_stock_metrics(ticker)
        all_metrics[ticker] = metrics

    valid_metrics_data = []
    for ticker, metrics in all_metrics.items():
        if metrics.get('date_range') and metrics.get('average_daily_volume', 0) >= daily_volume_threshold:
            metrics_row = {'Ticker': ticker}
            metrics_row.update(metrics)
            valid_metrics_data.append(metrics_row)

    if not valid_metrics_data:
        return pd.DataFrame() # Return empty DataFrame if no valid data

    return pd.DataFrame(valid_metrics_data)

def calculate_composite_scores(df):
    """Calculate z-scores and composite scores for ranking."""
    if df.empty:
        return pd.DataFrame() # Return empty DataFrame if input is empty

    higher_is_better = [
        'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'annualized_return',
        'upside_capture', 'momentum_6m', 'momentum_12m', 'max_drawdown',
    ]
    lower_is_better = [
        'annualized_volatility', 'daily_return_volatility', 'beta',
        'sector_beta', 'downside_capture'
    ]

    z_scores = df.copy()
    for col in higher_is_better + lower_is_better:
        if col in df.columns and not df[col].isnull().all() and df[col].std(ddof=0) != 0: # Check for NaNs and zero std dev
            z_scores[col] = (df[col] - df[col].mean()) / df[col].std(ddof=0)
        else:
            z_scores[col] = 0 # Assign 0 if column missing, all NaN, or no variation

    for col in lower_is_better:
        if col in z_scores.columns:
            z_scores[col] = -z_scores[col]

    metric_columns = [col for col in higher_is_better + lower_is_better if col in z_scores.columns]
    z_scores['composite_score'] = z_scores[metric_columns].sum(axis=1)

    return z_scores.sort_values(by='composite_score', ascending=False)

