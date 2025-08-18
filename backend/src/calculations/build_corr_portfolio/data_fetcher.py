"""
Data fetching module for correlation-aware portfolio builder.
Handles all historical price data retrieval operations.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.src.repositories.price_data import get_price_data_daily


class DataFetcher:
    """Handles fetching historical price data for portfolio assets."""
    
    def __init__(self, lookback_days: int = 252):
        """
        Initialize the data fetcher.
        
        Parameters:
        -----------
        lookback_days : int
            Number of days to look back for historical data (default 252 trading days)
        """
        self.lookback_days = lookback_days
        self.price_data = {}
    
    def fetch_all_price_data(self, tickers: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Fetch historical price data for all tickers in parallel.
        
        Parameters:
        -----------
        tickers : Dict[str, Dict]
            Dictionary with ticker symbols as keys
            
        Returns:
        --------
        Dict[str, Any]: Price data for each ticker
        """
        print("Fetching historical price data...")
        start_date = datetime.now() - timedelta(days=int(self.lookback_days * 1.5))  # Extra buffer
        end_date = datetime.now()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(get_price_data_daily, ticker, start_date, end_date): ticker 
                for ticker in tickers.keys()
            }
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data = future.result()
                    if data is not None and not data.empty:
                        self.price_data[ticker] = data
                        print(f"  ☑️  {ticker}: {len(data)} days of data")
                    else:
                        print(f"  ❌ {ticker}: No data available")
                except Exception as e:
                    print(f"  ❌ {ticker}: Error fetching data - {str(e)}")
        
        return self.price_data
