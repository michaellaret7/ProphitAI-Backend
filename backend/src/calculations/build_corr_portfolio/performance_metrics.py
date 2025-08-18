"""
Performance metrics module for correlation-aware portfolio builder.
Handles detailed performance calculations and analytics.
"""

import numpy as np
import pandas as pd
from typing import Dict


class PerformanceMetrics:
    """Handles detailed performance calculations for portfolios."""
    
    def __init__(self, portfolio_value: float, leverage: float = 1.0, trading_days: int = 252):
        """
        Initialize the performance metrics calculator.
        
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
    
    def calculate_detailed_performance_metrics(self, weights: Dict[str, float], 
                                              returns_data: pd.DataFrame) -> Dict:
        """
        Calculate detailed performance metrics over multiple time periods.
        
        Parameters:
        -----------
        weights : Dict[str, float]
            Portfolio weights for each ticker
        returns_data : pd.DataFrame
            Historical returns data
            
        Returns:
        --------
        Dict with detailed performance metrics
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
        
        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # Calculate various metrics
        metrics = {}
        
        # Total return
        total_return = cumulative_returns.iloc[-1] - 1
        metrics['total_return'] = total_return
        
        # Total profit in dollars (based on leveraged capital)
        leveraged_capital = self.portfolio_value * self.leverage
        metrics['total_profit'] = total_return * leveraged_capital
        
        # Annualized returns for different periods
        days_held = len(portfolio_returns)
        years_held = days_held / self.trading_days
        
        metrics['annualized_return'] = (cumulative_returns.iloc[-1] ** (1/years_held)) - 1
        
        # Calculate returns for each year
        portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
        yearly_returns = portfolio_returns.groupby(portfolio_returns.index.year).apply(
            lambda x: (1 + x).prod() - 1
        )
        
        metrics['yearly_returns'] = yearly_returns.to_dict()
        metrics['best_year'] = (yearly_returns.max(), yearly_returns.idxmax())
        metrics['worst_year'] = (yearly_returns.min(), yearly_returns.idxmin())
        
        # Monthly returns statistics
        monthly_returns = portfolio_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        metrics['avg_monthly_return'] = monthly_returns.mean()
        metrics['avg_monthly_profit'] = metrics['avg_monthly_return'] * leveraged_capital
        metrics['best_month'] = monthly_returns.max()
        metrics['worst_month'] = monthly_returns.min()
        metrics['positive_months'] = (monthly_returns > 0).sum() / len(monthly_returns)
        
        # Risk metrics
        metrics['annual_volatility'] = portfolio_returns.std() * np.sqrt(self.trading_days)
        metrics['downside_deviation'] = portfolio_returns[portfolio_returns < 0].std() * np.sqrt(self.trading_days)
        
        # Sharpe and Sortino ratios
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        excess_returns = metrics['annualized_return'] - risk_free_rate
        metrics['sharpe_ratio'] = excess_returns / metrics['annual_volatility']
        metrics['sortino_ratio'] = excess_returns / metrics['downside_deviation']
        
        # Drawdown metrics
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        metrics['max_drawdown'] = drawdown.min()
        metrics['avg_drawdown'] = drawdown[drawdown < 0].mean()
        
        # Calmar ratio (annualized return / max drawdown)
        metrics['calmar_ratio'] = metrics['annualized_return'] / abs(metrics['max_drawdown'])
        
        # Win rate
        metrics['daily_win_rate'] = (portfolio_returns > 0).sum() / len(portfolio_returns)
        
        # Value at Risk (95% confidence)
        metrics['var_95'] = np.percentile(portfolio_returns, 5)
        metrics['cvar_95'] = portfolio_returns[portfolio_returns <= metrics['var_95']].mean()
        
        return metrics
