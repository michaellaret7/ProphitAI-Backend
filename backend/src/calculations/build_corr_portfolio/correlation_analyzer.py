"""
Correlation analysis module for correlation-aware portfolio builder.
Handles correlation and covariance matrix calculations.
"""

import numpy as np
import pandas as pd


class CorrelationAnalyzer:
    """Handles correlation and covariance matrix calculations."""
    
    def __init__(self, trading_days: int = 252):
        """
        Initialize the correlation analyzer.
        
        Parameters:
        -----------
        trading_days : int
            Number of trading days per year (default 252)
        """
        self.trading_days = trading_days
        self.correlation_matrix = None
        self.covariance_matrix = None
    
    def calculate_correlation_matrix(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the correlation matrix of asset returns.
        
        Parameters:
        -----------
        returns_data : pd.DataFrame
            DataFrame of returns for all assets
            
        Returns:
        --------
        pd.DataFrame: Correlation matrix
        """
        if returns_data.empty:
            raise ValueError("Returns data is empty")
        
        # Use pairwise correlation to handle missing data
        self.correlation_matrix = returns_data.corr(method='pearson')
        print(f"\nCorrelation matrix calculated ({self.correlation_matrix.shape[0]}x{self.correlation_matrix.shape[1]})")
        
        # Print average correlations
        mask = np.ones_like(self.correlation_matrix, dtype=bool)
        np.fill_diagonal(mask, 0)
        # Filter out NaN values when calculating average
        corr_values = self.correlation_matrix.values[mask]
        avg_corr = np.nanmean(corr_values)
        print(f"  Average pairwise correlation: {avg_corr:.3f}")
        
        return self.correlation_matrix
    
    def calculate_covariance_matrix(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the covariance matrix of asset returns.
        
        Parameters:
        -----------
        returns_data : pd.DataFrame
            DataFrame of returns for all assets
            
        Returns:
        --------
        pd.DataFrame: Annualized covariance matrix
        """
        if returns_data.empty:
            raise ValueError("Returns data is empty")
        
        # Annualized covariance matrix using pairwise covariance to handle missing data
        self.covariance_matrix = returns_data.cov() * self.trading_days
        
        # Fill any remaining NaN values in covariance matrix with zeros for missing ticker pairs
        # This is conservative - assumes no correlation for ticker pairs with no overlapping data
        self.covariance_matrix = self.covariance_matrix.fillna(0)
        
        return self.covariance_matrix
