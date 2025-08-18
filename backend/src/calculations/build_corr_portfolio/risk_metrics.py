"""
Risk metrics module for correlation-aware portfolio builder.
Handles VaR calculations and risk contribution analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List


class RiskMetrics:
    """Handles risk calculations including VaR and risk contributions."""
    
    def __init__(self, portfolio_value: float, leverage: float = 1.0, trading_days: int = 252):
        """
        Initialize the risk metrics calculator.
        
        Parameters:
        -----------
        portfolio_value : float
            Total portfolio value in dollars
        leverage : float
            Leverage multiplier
        trading_days : int
            Number of trading days per year
        """
        self.portfolio_value = portfolio_value
        self.leverage = leverage
        self.trading_days = trading_days
    
    def calculate_risk_contributions(self, weights: Dict[str, float], covariance_matrix) -> Dict[str, float]:
        """
        Calculate each asset's contribution to portfolio risk.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
        covariance_matrix : pd.DataFrame
            Covariance matrix of returns
            
        Returns:
        --------
        Dict[str, float]: Risk contribution for each asset
        """
        tickers = list(weights.keys())
        w = np.array([weights[ticker] for ticker in tickers])
        cov = covariance_matrix.loc[tickers, tickers].values
        
        # Portfolio variance
        portfolio_variance = np.dot(w.T, np.dot(cov, w))
        
        # Marginal contributions to variance
        marginal_contrib = np.dot(cov, w)
        
        # Risk contributions
        risk_contributions = {}
        for i, ticker in enumerate(tickers):
            contrib = w[i] * marginal_contrib[i] / portfolio_variance
            risk_contributions[ticker] = contrib
        
        return risk_contributions
    
    def calculate_portfolio_var(self, weights: Dict[str, float], returns_data: pd.DataFrame,
                               confidence_levels: List[float] = [0.95, 0.99]) -> Dict[str, Dict]:
        """
        Calculate portfolio VaR at different confidence levels.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
        returns_data : pd.DataFrame
            Historical returns data
        confidence_levels : List[float]
            Confidence levels for VaR calculation
            
        Returns:
        --------
        Dict with VaR results at different confidence levels
        """
        if returns_data.empty:
            return {}
        
        # Calculate portfolio returns
        tickers = list(weights.keys())
        portfolio_returns = pd.Series(0, index=returns_data.index)
        
        for ticker in tickers:
            if ticker in returns_data.columns:
                # Only add to portfolio returns where ticker data exists
                ticker_returns = returns_data[ticker].fillna(0)  # Fill NaN with 0 for missing data
                portfolio_returns += ticker_returns * weights[ticker]
        
        # Calculate VaR for different confidence levels
        var_results = {}
        for conf_level in confidence_levels:
            var_percentile = (1 - conf_level) * 100
            daily_var = np.percentile(portfolio_returns, var_percentile)
            
            # Annualized VaR (assuming normal distribution for scaling)
            annual_var = daily_var * np.sqrt(self.trading_days)
            
            # VaR in dollar terms (based on leveraged capital)
            dollar_var = annual_var * self.portfolio_value * self.leverage
            
            var_results[f'var_{int(conf_level*100)}'] = {
                'daily': daily_var,
                'annual': annual_var,
                'dollar': dollar_var
            }
        
        return var_results
    
    def calculate_portfolio_metrics(self, weights: Dict[str, float], covariance_matrix, 
                                   returns_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate key portfolio metrics given weights.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
        covariance_matrix : pd.DataFrame
            Covariance matrix
        returns_data : pd.DataFrame
            Historical returns data
            
        Returns:
        --------
        Dict[str, float]: Portfolio metrics
        """
        # Convert to numpy array
        tickers = list(weights.keys())
        w = np.array([weights[ticker] for ticker in tickers])
        
        # Get covariance matrix for these tickers
        cov = covariance_matrix.loc[tickers, tickers].values
        
        # Portfolio volatility
        portfolio_variance = np.dot(w.T, np.dot(cov, w))
        portfolio_vol = np.sqrt(portfolio_variance)
        
        # Expected returns (using historical mean)
        mean_returns = returns_data[tickers].mean() * self.trading_days
        portfolio_return = np.dot(w, mean_returns)
        
        # Diversification ratio
        weighted_avg_vol = np.dot(np.abs(w), np.sqrt(np.diag(cov)))
        diversification_ratio = weighted_avg_vol / portfolio_vol
        
        # Effective number of assets (using Herfindahl index)
        herfindahl = np.sum(w**2)
        effective_n_assets = 1 / herfindahl if herfindahl > 0 else 0
        
        return {
            'annual_volatility': portfolio_vol,
            'expected_return': portfolio_return,
            'sharpe_ratio': portfolio_return / portfolio_vol if portfolio_vol > 0 else 0,
            'diversification_ratio': diversification_ratio,
            'effective_n_assets': effective_n_assets
        }
