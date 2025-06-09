import pandas as pd
import numpy as np
import logging
from backend.src.utils.caching import cache_result
from backend.src.utils.file_utils import load_schema_data
from backend.src.portfolio_optimization.phase_two.data_retrieval import get_daily_closing_prices
from backend.src.utils.financial_calculations import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_annualized_return,
    calculate_volatility,
    calculate_max_drawdown,
    calculate_beta,
    calculate_alpha,
    calculate_var,
    calculate_treynor_ratio,
    calculate_information_ratio
)

daily_volume_threshold = 10_000

# Get a logger instance
logger = logging.getLogger(__name__)

@cache_result
def calculate_stock_metrics(ticker):
   """
   Calculate comprehensive risk-adjusted performance metrics for a stock.
   
   Computes Sharpe ratio, volatility, beta, momentum, and other financial metrics
   using historical price data and market benchmarks for comparative analysis.
   
   Args:
       ticker: The stock ticker symbol (e.g., 'AAPL', 'MSFT').
   
   Returns:
       Dict: Dictionary containing calculated financial metrics including ratios,
       returns, volatility, beta, momentum, and volume data.
   """
   # Get price data for the ticker
   price_data = get_daily_closing_prices(ticker)
   spy_data = get_daily_closing_prices('spy')
   
   # Check if ticker is an ETF (simple check based on common ETF tickers from screenshot)
   etf_list = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC"]
   is_etf = ticker.upper() in etf_list
   
   # Return default values if no price data is available
   if price_data is None or price_data.empty:
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
   df = price_data.copy()
   df['daily_return'] = df['close'].pct_change()
   
   # Calculate Average Daily Volume
   average_daily_volume = df['volume'].mean() if 'volume' in df and not df['volume'].empty else 0
   
   # Drop NaN values (first row will have NaN return)
   df = df.dropna(subset=['daily_return']).copy()
   
   if df.empty:
        # Handle case where all data is NaN after pct_change and dropna
        # (e.g. if only one day of data was present in price_data)
        print(f"Not enough data for {ticker} to calculate returns.")
        # Return default metrics as above
        default_metrics = {
            "ticker": ticker, "sharpe_ratio": 0, "sortino_ratio": 0, "calmar_ratio": 0,
            "annualized_return": 0, "annualized_volatility": 0, "daily_return_volatility": 0,
            "max_drawdown": 0, "beta": 0, "date_range": [], "upside_capture": 0, "downside_capture": 0,
            "momentum_6m": 0, "momentum_12m": 0, "average_daily_volume": int(round(average_daily_volume)) # Keep calculated volume
        }
        if not is_etf: default_metrics.update({"sector_beta": 0})
        return default_metrics

   daily_returns = df['daily_return']
   df['cumulative_return'] = (1 + daily_returns).cumprod()

   # Calculate metrics using utility functions
   annual_sharpe = calculate_sharpe_ratio(daily_returns, risk_free_rate=risk_free_rate, annualize=True)
   annual_volatility = calculate_volatility(daily_returns, annualize=True)
   max_dd = calculate_max_drawdown(df['cumulative_return'])
   annual_ret = calculate_annualized_return(daily_returns)
   sortino_val = calculate_sortino_ratio(daily_returns, risk_free_rate=risk_free_rate, annualize=True)
   calmar_val = calculate_calmar_ratio(daily_returns, max_dd)
   std_daily_return = calculate_volatility(daily_returns, annualize=False) # Daily volatility

   # Calculate Momentum Scores (6-month and 12-month)
   momentum_6m = 0
   momentum_12m = 0
   if len(df) >= 126:
      momentum_6m = (1 + df['daily_return'].iloc[-126:]).prod() - 1
   if len(df) >= 252:
      momentum_12m = (1 + df['daily_return'].iloc[-252:]).prod() - 1
   
   # Calculate Beta (market risk)
   beta_val = 0
   alpha_val = 0
   treynor_val = 0
   information_ratio_val = 0
   upside_capture = 0
   downside_capture = 0
   if spy_data is not None and not spy_data.empty:
      spy_df = spy_data.copy()
      spy_df['daily_return'] = spy_df['close'].pct_change()
      spy_df = spy_df.dropna(subset=['daily_return'])
      
      merged_data = pd.merge(
         df[['date', 'daily_return']], 
         spy_df[['date', 'daily_return']], 
         on='date', 
         how='inner',
         suffixes=('_stock', '_market')
      )
      
      if not merged_data.empty and len(merged_data) > 1: # Beta needs more than one point
         # Portfolio and benchmark daily returns aligned
         portfolio_returns = merged_data['daily_return_stock']
         benchmark_returns = merged_data['daily_return_market']

         # Systematic risk
         beta_val = calculate_beta(portfolio_returns, benchmark_returns)

         # Risk-adjusted performance metrics dependent on beta / benchmark
         try:
            alpha_val = calculate_alpha(portfolio_returns, benchmark_returns, risk_free_rate, beta_val)
         except Exception as e:
            print(f"Warning: Failed to calculate alpha for {ticker}: {e}")
            alpha_val = 0

         try:
            treynor_val = calculate_treynor_ratio(portfolio_returns, benchmark_returns, risk_free_rate, beta_val)
         except Exception as e:
            print(f"Warning: Failed to calculate Treynor Ratio for {ticker}: {e}")
            treynor_val = 0

         try:
            information_ratio_val = calculate_information_ratio(portfolio_returns, benchmark_returns)
         except Exception as e:
            print(f"Warning: Failed to calculate Information Ratio for {ticker}: {e}")
            information_ratio_val = 0

         # Upside / Downside capture after benchmark alignment
         up_days = merged_data[merged_data['daily_return_market'] > 0]
         down_days = merged_data[merged_data['daily_return_market'] < 0]
         
         if not up_days.empty and up_days['daily_return_market'].mean() != 0:
            avg_stock_return_up = up_days['daily_return_stock'].mean()
            avg_benchmark_return_up = up_days['daily_return_market'].mean()
            upside_capture = avg_stock_return_up / avg_benchmark_return_up
         
         if not down_days.empty and down_days['daily_return_market'].mean() != 0:
            avg_stock_return_down = down_days['daily_return_stock'].mean()
            avg_benchmark_return_down = down_days['daily_return_market'].mean()
            downside_capture = avg_stock_return_down / avg_benchmark_return_down
   
   # Calculate historical 95% VaR (lower is better)
   try:
      var_pct, _ = calculate_var(daily_returns, confidence_level=0.95, amount=1)
   except Exception as e:
      print(f"Warning: Failed to calculate VaR for {ticker}: {e}")
      var_pct = 0
   
   # Initialize sector-specific variables
   sector = None
   sector_etf = None
   sector_beta = 0
   
   sector_etf_map = {
      "technology": "XLK", "financial": "XLF", "health_care": "XLV",
      "consumer_discretionary": "XLY", "consumer_staples": "XLP", "energy": "XLE",
      "industrial": "XLI", "materials": "XLB", "utilities": "XLU",
      "real_estate": "XLRE", "communication": "XLC"
   }
   
   if not is_etf:
      try:
         schema_data = load_schema_data()
         for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            for schema_name_val, schema_info_val in schemas.items():
               tables = schema_info_val.get('tables', {})
               for table_name_val, table_info_val in tables.items():
                  tickers_list = table_info_val.get('tickers', [])
                  if ticker.upper() in [t.upper() for t in tickers_list]:
                     sector = sector_name
                     break
               if sector: break
            if sector: break
         
         if sector:
            matched_sector_key = next((key for key in sector_etf_map if key in sector.lower()), None)
            if matched_sector_key:
               sector_etf = sector_etf_map[matched_sector_key]
               sector_etf_data = get_daily_closing_prices(sector_etf)
               if sector_etf_data is not None and not sector_etf_data.empty:
                  sector_etf_df = sector_etf_data.copy()
                  sector_etf_df['daily_return'] = sector_etf_df['close'].pct_change()
                  sector_etf_df = sector_etf_df.dropna(subset=['daily_return'])
                  
                  merged_sector_data = pd.merge(
                     df[['date', 'daily_return']], 
                     sector_etf_df[['date', 'daily_return']], 
                     on='date', 
                     how='inner',
                     suffixes=('_stock', '_sector')
                  )
                  if not merged_sector_data.empty and len(merged_sector_data) > 1:
                     sector_beta = calculate_beta(merged_sector_data['daily_return_stock'], merged_sector_data['daily_return_sector'])
      except Exception as e:
         print(f"Error calculating sector beta for {ticker}: {e}")
   
   metrics = {
      "sharpe_ratio": float(round(annual_sharpe, 2)),
      "sortino_ratio": float(round(sortino_val, 2)),
      "calmar_ratio": float(round(calmar_val, 2)),
      "annualized_return": float(round(annual_ret, 4)),
      "annualized_volatility": float(round(annual_volatility, 2)),
      "daily_return_volatility": float(round(std_daily_return, 4)), # Increased precision for daily
      "max_drawdown": float(round(max_dd, 4)), # Increased precision for drawdown
      "beta": float(round(beta_val, 2)),
      "alpha": float(round(alpha_val, 4)),
      "var_95": float(round(var_pct, 4)),
      "treynor_ratio": float(round(treynor_val, 2)),
      "information_ratio": float(round(information_ratio_val, 2)),
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
    """
    Calculate metrics for tickers and filter out those with insufficient data.
    
    Processes a list of tickers to compute financial metrics and applies
    volume and date range filters to ensure data quality.
    
    Args:
        ticker_list: List of ticker symbols to analyze.
        
    Returns:
        pd.DataFrame: DataFrame containing valid tickers with their calculated metrics,
        or empty DataFrame if no tickers pass filtering criteria.
    """
    all_metrics = {}
    logger.info(f"Calculating and filtering metrics for tickers: {ticker_list}")
    for ticker in ticker_list:
        logger.debug(f"Calculating metrics for ticker: {ticker}")
        metrics = calculate_stock_metrics(ticker)
        all_metrics[ticker] = metrics
        logger.debug(f"Metrics for {ticker}: {metrics}")

    valid_metrics_data = []
    for ticker, metrics in all_metrics.items():
        # Log the metrics being evaluated for filtering
        logger.debug(f"Evaluating filter conditions for {ticker}: Date range present: {bool(metrics.get('date_range'))}, Avg Daily Volume: {metrics.get('average_daily_volume', 0)}")
        if metrics.get('date_range') and metrics.get('average_daily_volume', 0) >= daily_volume_threshold:
            metrics_row = {'Ticker': ticker}
            metrics_row.update(metrics)
            valid_metrics_data.append(metrics_row)
            logger.debug(f"{ticker} passed filtering.")
        else:
            logger.info(f"{ticker} failed filtering. Date range: {metrics.get('date_range')}, Avg Daily Volume: {metrics.get('average_daily_volume', 0)}")

    if not valid_metrics_data:
        logger.warning(f"No valid metrics data found for tickers: {ticker_list}")
        return pd.DataFrame() # Return empty DataFrame if no valid data

    logger.info(f"Finished calculating and filtering metrics. Found {len(valid_metrics_data)} valid tickers.")
    return pd.DataFrame(valid_metrics_data)

def calculate_composite_scores(df):
    """
    Calculate z-scores and composite scores for ranking stocks.
    
    Computes standardized z-scores for all metrics and creates composite scores
    for ranking, with proper handling of directional preferences (higher/lower is better).
    
    Args:
        df: DataFrame containing stock metrics for scoring.
        
    Returns:
        pd.DataFrame: DataFrame sorted by composite score in descending order,
        or empty DataFrame if input is empty.
    """
    if df.empty:
        return pd.DataFrame() # Return empty DataFrame if input is empty

    higher_is_better = [
        'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'annualized_return',
        'upside_capture', 'momentum_6m', 'momentum_12m', 'max_drawdown',
        'alpha', 'treynor_ratio', 'information_ratio'
    ]
    lower_is_better = [
        'annualized_volatility', 'daily_return_volatility', 'beta',
        'sector_beta', 'downside_capture', 'var_95'
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

if __name__ == "__main__":
   x = calculate_stock_metrics('AAPL')
   print(x)