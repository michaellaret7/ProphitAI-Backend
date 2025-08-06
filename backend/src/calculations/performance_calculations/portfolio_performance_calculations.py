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
    
    def calculate_upside_downside_capture(self, fund_returns: pd.Series, benchmark_returns: pd.Series):
        """
        Calculate upside and downside capture ratios for given fund and benchmark returns.
        
        :param fund_returns: Fund return series
        :param benchmark_returns: Benchmark return series
        :return: Dictionary with upside capture, downside capture, and capture ratio
        """
        # Align the series and remove NaN values
        aligned_data = pd.DataFrame({
            'fund': fund_returns,
            'benchmark': benchmark_returns
        }).dropna()
        
        if aligned_data.empty:
            return {
                'upside_capture': np.nan,
                'downside_capture': np.nan,
                'capture_ratio': np.nan,
                'capture_spread': np.nan
            }
        
        fund_aligned = aligned_data['fund']
        benchmark_aligned = aligned_data['benchmark']
        
        # Separate up and down periods based on benchmark performance
        up_periods = benchmark_aligned >= 0
        down_periods = benchmark_aligned < 0
        
        # Calculate upside capture ratio
        if up_periods.sum() > 0:
            fund_up_returns = fund_aligned[up_periods]
            benchmark_up_returns = benchmark_aligned[up_periods]
            
            # Calculate compound returns for up periods
            fund_up_compound = (1 + fund_up_returns).prod() - 1
            benchmark_up_compound = (1 + benchmark_up_returns).prod() - 1
            
            upside_capture = fund_up_compound / benchmark_up_compound if benchmark_up_compound != 0 else np.nan
        else:
            upside_capture = np.nan
            
        # Calculate downside capture ratio
        if down_periods.sum() > 0:
            fund_down_returns = fund_aligned[down_periods]
            benchmark_down_returns = benchmark_aligned[down_periods]
            
            # Calculate compound returns for down periods
            fund_down_compound = (1 + fund_down_returns).prod() - 1
            benchmark_down_compound = (1 + benchmark_down_returns).prod() - 1
            
            downside_capture = fund_down_compound / benchmark_down_compound if benchmark_down_compound != 0 else np.nan
        else:
            downside_capture = np.nan
            
        # Calculate overall capture ratio and spread
        capture_ratio = upside_capture / downside_capture if (downside_capture != 0 and not np.isnan(downside_capture)) else np.nan
        capture_spread = upside_capture - downside_capture if (not np.isnan(upside_capture) and not np.isnan(downside_capture)) else np.nan
        
        return {
            'upside_capture': upside_capture,
            'downside_capture': downside_capture,
            'capture_ratio': capture_ratio,
            'capture_spread': capture_spread
        }