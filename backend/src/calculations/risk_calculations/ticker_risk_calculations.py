import pandas as pd
import numpy as np
from backend.src.repositories.market_data.ticker_repository import get_ticker_price_data
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.returns_calculations.portfolio_returns_calculations import CalculatePortfolioReturns
from datetime import datetime, timedelta
from typing import Dict
from backend.src.calculations.risk_calculations.portfolio_risk_calculations import PortfolioRiskCalculations
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
import scipy.stats as stats

class TickerRiskCalculations:
    def __init__(self, ticker):
        self.ticker = ticker
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()
        # Fetch price data and ensure datetime index
        raw_data = get_ticker_price_data(
            ticker,
            start_date.isoformat(),
            end_date.isoformat(),
            "1d"
        )
        if raw_data is not None and 'date' in raw_data.columns:
            raw_data['date'] = pd.to_datetime(raw_data['date'])
            raw_data.set_index('date', inplace=True)

        self.price_data = raw_data
        self.returns = CalculateTickerReturns(self.price_data).calculate_daily_total_returns()

        self.confidence_level = 0.99
        self.trading_days = 252
        self.z_score = stats.norm.ppf(self.confidence_level)
        
        # Common z-scores for reference
        self.z_scores = {
            0.90: 1.28,
            0.95: 1.65,
            0.99: 2.33,
            0.995: 2.58,
            0.999: 3.09
        }
    
    def calculate_ticker_correlation(self, portfolio_returns):
        """
        Calculates the Pearson correlation coefficient between the ticker's returns and the portfolio returns.
        """
        # Ensure portfolio_returns is a pandas Series
        if not isinstance(portfolio_returns, pd.Series):
            portfolio_series = pd.Series(portfolio_returns)
        else:
            portfolio_series = portfolio_returns
        # Align indexes on common dates
        common_index = self.returns.index.intersection(portfolio_series.index)
        if common_index.empty:
            return np.nan
        ticker_returns_aligned = self.returns.loc[common_index]
        portfolio_returns_aligned = portfolio_series.loc[common_index]
        # Compute and return correlation
        return ticker_returns_aligned.corr(portfolio_returns_aligned)
    
    def calculate_ticker_annualized_volatility(self):
        """
        Calculates the volatility of the ticker's returns.
        """
        # Use closing price series to compute volatility and avoid DataFrame.std warning
        return VolatilityFactors(self.price_data['close']).annualized_volatility(lookback_days=252)
    
    def _calculate_fund_var(self, fund_nav: float, target_fund_annual_vol: float) -> Dict[str, float]:
        """Helper to calculate fund VaR."""
        # This uses a simple VaR calculation that doesn't depend on portfolio holdings
        prc = PortfolioRiskCalculations(confidence_level=self.confidence_level, trading_days=self.trading_days)
        return prc.calculate_var(portfolio_value=fund_nav, annual_volatility=target_fund_annual_vol)

    def calculate_ticker_position_size(self, fund_nav: float, target_fund_annual_vol: float, position_annual_vol: float, risk_allocation: float, correlation: float = 0.0) -> Dict[str, float]:
        """
        Calculate position size based on risk allocation
        
        Parameters:
        -----------
        fund_nav : float
            Total fund NAV (Net Asset Value)
        fund_annual_vol : float
            Target fund annual volatility (e.g., 0.10 for 10%)
        position_annual_vol : float
            Annual volatility of the position (e.g., 0.20 for 20%)
        risk_allocation : float
            Percentage of fund VaR to allocate (e.g., 0.05 for 5%)
        correlation : float
            Correlation with existing portfolio (default 0)
            
        Returns:
        --------
        dict : Position sizing details
        """
        # Calculate fund VaR
        fund_var = self._calculate_fund_var(fund_nav, target_fund_annual_vol)
        
        # Risk budget for this position
        position_var_budget = fund_var['var_dollars'] * risk_allocation
        
        # Position daily volatility
        position_daily_vol = position_annual_vol / np.sqrt(self.trading_days)
        
        # Basic position size (ignoring correlation)
        position_size = position_var_budget / (self.z_score * position_daily_vol)
        
        # Adjust for correlation (simplified - assumes position is small relative to portfolio)
        correlation_adjustment = np.sqrt(1 - correlation**2)
        adjusted_position_size = position_size * correlation_adjustment
        
        return {
            'position_size': round(float(position_size), 5),
            'correlation_adjusted_position_size': round(float(adjusted_position_size), 5),
            'position_weight': round(float(position_size / fund_nav), 5),
            'correlation_adjusted_weight': round(float(adjusted_position_size / fund_nav), 5),
            'position_var_budget': round(float(position_var_budget), 5),
            'position_daily_vol': round(float(position_daily_vol), 5),
            'fund_var_dollars': round(float(fund_var['var_dollars']), 5)
        }
    

