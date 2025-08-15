"""
Returns calculation module for correlation-aware portfolio builder.
Handles daily returns calculations and data preparation.
"""

import pandas as pd
from typing import Dict, Any


class ReturnsCalculator:
    """Handles calculation of daily returns for portfolio assets."""
    
    def __init__(self):
        """Initialize the returns calculator."""
        self.returns_data = pd.DataFrame()
    
    def calculate_returns(self, price_data: Dict[str, Any], tickers: Dict[str, Dict]) -> pd.DataFrame:
        """
        Calculate daily returns for all assets and combine into a DataFrame.
        
        Parameters:
        -----------
        price_data : Dict[str, Any]
            Price data for each ticker
        tickers : Dict[str, Dict]
            Dictionary with ticker information
            
        Returns:
        --------
        pd.DataFrame: Combined returns data
        """
        print("\nCalculating returns...")
        returns_dict = {}
        ticker_start_dates = {}
        
        for ticker, data in price_data.items():
            # Ensure datetime index
            if 'date' in data.columns:
                data = data.copy()
                data['date'] = pd.to_datetime(data['date'])
                data.set_index('date', inplace=True)
            
            # Calculate returns
            returns = data['close'].pct_change().dropna()
            returns_dict[ticker] = returns
            
            # Track start date for each ticker
            if not returns.empty:
                ticker_start_dates[ticker] = returns.index[0]
        
        # Combine into DataFrame - use 'outer' join to keep all dates
        self.returns_data = pd.DataFrame(returns_dict)
        
        # Print information about data availability
        print(f"\n  Data availability by ticker:")
        for ticker, start_date in sorted(ticker_start_dates.items(), key=lambda x: x[1]):
            print(f"    {ticker}: starts from {start_date.strftime('%Y-%m-%d')}")
        
        # Find the date when we have at least 80% of tickers available
        min_tickers_required = int(len(tickers) * 0.8)
        data_availability = self.returns_data.notna().sum(axis=1)
        sufficient_data_mask = data_availability >= min_tickers_required
        
        if sufficient_data_mask.any():
            first_sufficient_date = self.returns_data[sufficient_data_mask].index[0]
            print(f"\n  Using data from {first_sufficient_date.strftime('%Y-%m-%d')} onwards (80% ticker coverage)")
            # Filter to dates with sufficient ticker coverage
            self.returns_data = self.returns_data[sufficient_data_mask]
        
        print(f"  Combined returns shape: {self.returns_data.shape}")
        print(f"  Date range: {self.returns_data.index[0].strftime('%Y-%m-%d')} to {self.returns_data.index[-1].strftime('%Y-%m-%d')}")
        
        return self.returns_data
