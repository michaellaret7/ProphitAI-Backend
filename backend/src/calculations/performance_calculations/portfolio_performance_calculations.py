import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from backend.src.calculations.returns_calculations.portfolio_returns_calculations import CalculatePortfolioReturns


class PortfolioPerformanceCalculations:
    """
    Efficient portfolio performance metrics calculator.
    Implements Sortino and Calmar ratios with reusable patterns.
    """
    
    def __init__(
        self, 
        tickers_weights: Dict[str, float], 
        start_date: str, 
        end_date: str,
        risk_free_rate: float = 0.04/252  # Daily risk-free rate (4% annual / 252 trading days)
    ):
        """
        Initialize portfolio performance calculator.
        
        :param tickers_weights: Dictionary with tickers as keys and weights as values
        :param start_date: Start date for the analysis (YYYY-MM-DD format)
        :param end_date: End date for the analysis (YYYY-MM-DD format)
        :param risk_free_rate: Daily risk-free rate (default: 4% annual / 252 trading days)
        """
        self.tickers_weights = tickers_weights
        self.start_date = start_date
        self.end_date = end_date
        self.risk_free_rate = risk_free_rate
        
        # Initialize portfolio returns calculator
        self.returns_calculator = CalculatePortfolioReturns(
            tickers_weights=tickers_weights,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_daily_returns(self) -> pd.Series:
        """Get daily returns."""
        return self.returns_calculator.calculate_daily_total_returns()
    
    def get_annualized_return(self) -> float:
        """Get annualized return."""
        return self.returns_calculator.calculate_annualized_total_return()
    
    def calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        daily_returns = self.get_daily_returns()
        if daily_returns.empty:
            return 0.0
        
        cumulative = (1 + daily_returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        safe_running_max = np.where(running_max == 0, np.nan, running_max)
        drawdown = (cumulative - safe_running_max) / safe_running_max
        return np.nanmin(drawdown) if not np.all(np.isnan(drawdown)) else 0.0
    
    def sortino_ratio(self, target_return: Optional[float] = None, trading_days: int = 252) -> float:
        """
        Calculate Sortino Ratio for the portfolio.
        
        :param target_return: Target return threshold (default: risk-free rate)
        :param trading_days: Number of trading days for annualization (default: 252)
        :return: Annualized Sortino ratio
        """
        if target_return is None:
            target_return = self.risk_free_rate
        
        daily_returns = self.get_daily_returns()
        if daily_returns.empty:
            return np.nan
        
        excess_returns = daily_returns - self.risk_free_rate
        downside_returns = daily_returns[daily_returns < target_return] - target_return
        
        if len(downside_returns) == 0:
            return np.inf
        
        # Calculate downside deviation
        downside_deviation = np.sqrt(np.mean(downside_returns**2))
        
        if downside_deviation == 0:
            return np.nan
        
        # Daily Sortino ratio
        daily_sortino = np.mean(excess_returns) / downside_deviation
        
        # Annualize the Sortino ratio
        return daily_sortino * np.sqrt(trading_days)
    
    def sharpe_ratio(self, trading_days: int = 252) -> float:
        """
        Calculate Sharpe Ratio for the portfolio.
        
        :param trading_days: Number of trading days for annualization (default: 252)
        :return: Annualized Sharpe ratio
        """
        daily_returns = self.get_daily_returns()
        if daily_returns.empty:
            return np.nan
        
        excess_returns = daily_returns - self.risk_free_rate
        std_excess_returns = np.std(excess_returns, ddof=1)
        
        if std_excess_returns == 0:
            return np.nan
        
        # Daily Sharpe ratio
        daily_sharpe = np.mean(excess_returns) / std_excess_returns
        
        # Annualize the Sharpe ratio
        return daily_sharpe * np.sqrt(trading_days)
    
    def calmar_ratio(self) -> float:
        """
        Calculate Calmar Ratio for the portfolio.
        
        :return: Calmar ratio (annualized return / max drawdown)
        """
        ann_return = self.get_annualized_return()
        max_dd = abs(self.calculate_max_drawdown())
        
        if max_dd == 0:
            return np.inf
        
        return ann_return / max_dd
