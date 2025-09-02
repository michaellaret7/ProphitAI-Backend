import pandas as pd
import numpy as np
from backend.src.repositories.price_data import get_price_data_daily, fetch_bulk_price_data_for_tickers
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
        raw_data = get_price_data_daily(
            ticker,
            start_date,
            end_date
        )
        if raw_data is not None and 'date' in raw_data.columns:
            raw_data['date'] = pd.to_datetime(raw_data['date'])
            raw_data.set_index('date', inplace=True)

        self.price_data = raw_data
        self.returns = CalculateTickerReturns(self.price_data, ticker).calculate_daily_total_returns()

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
    

def calculate_beta(ticker: str, benchmark_ticker: str = None, period_days: int = 730):
    """
    Calculates the beta of a ticker against a benchmark using historical data.

    Parameters:
    - ticker (str): The ticker symbol of the stock.
    - benchmark_ticker (str): The ticker symbol of the benchmark (e.g., 'SPY').
    - period_days (int): The number of past days to use for the beta calculation.

    Returns:
    - float: The calculated beta value, or None if data is insufficient.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Fetch data for the ticker and the benchmark
    ticker_df = get_price_data_daily(ticker, start_date_str, end_date_str)
    if benchmark_ticker:
        benchmark_df = get_price_data_daily(benchmark_ticker, start_date_str, end_date_str)
    else:
        benchmark_df = get_price_data_daily(ticker, start_date_str, end_date_str)

    if ticker_df is None or benchmark_df is None or ticker_df.empty or benchmark_df.empty:
        print(f"Warning: Could not fetch price data for {ticker} or {benchmark_ticker}.")
        return None

    # Set 'date' as index and extract 'close' prices
    ticker_df['date'] = pd.to_datetime(ticker_df['date'])
    ticker_df = ticker_df.set_index('date')
    ticker_prices = ticker_df['close']

    benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
    benchmark_df = benchmark_df.set_index('date')
    benchmark_prices = benchmark_df['close']

    # Calculate returns
    ticker_returns = ticker_prices.pct_change(fill_method=None).dropna()
    benchmark_returns = benchmark_prices.pct_change(fill_method=None).dropna()

    # Align data by index (timestamps)
    returns_df = pd.concat([ticker_returns, benchmark_returns], axis=1, join='inner')
    returns_df.columns = [ticker, benchmark_ticker]

    if len(returns_df) < 2:
        print(f"Warning: Not enough overlapping data for {ticker} to calculate beta.")
        return None

    # Calculate covariance and variance using pandas built-in methods
    covariance = returns_df[ticker].cov(returns_df[benchmark_ticker])
    variance = returns_df[benchmark_ticker].var()

    if variance is None or variance == 0:
        print(f"Warning: Benchmark variance is zero for {benchmark_ticker}, cannot calculate beta.")
        return None

    beta = covariance / variance
    
    return beta

def calculate_up_down_beta(stock_ticker: str, market_ticker: str = 'SPY', start_date_str: str = None, end_date_str: str = None, frequency: str = None):
    """
    Calculate up beta and down beta for a stock relative to the market.
    
    Parameters:
    - stock_ticker: str - The stock ticker symbol
    - market_ticker: str - The market ticker symbol (default: 'SPY')
    - start_date_str: str - Start date for the price data
    - end_date_str: str - End date for the price data
    - frequency: str - Frequency of the price data
    
    Returns:
    - dict: Dictionary containing up_beta and down_beta values
    """
    
    # Fetch price data for stock and market
    tickers = [stock_ticker, market_ticker]
    price_data = fetch_bulk_price_data_for_tickers(tickers=tickers, start_date_str=start_date_str, end_date_str=end_date_str, frequency=frequency)
    
    # Convert to DataFrame and calculate returns
    price_df = pd.DataFrame(price_data)
    returns_df = price_df.pct_change(fill_method=None).dropna()
    
    # Create DataFrame with Market and Stock columns
    df = pd.DataFrame({
        'Market': returns_df[market_ticker],
        'Stock': returns_df[stock_ticker]
    })
    
    # Calculate up and down betas
    up = df[df['Market'] > 0]
    down = df[df['Market'] < 0]
    
    up_beta = up['Stock'].cov(up['Market']) / up['Market'].var()
    down_beta = down['Stock'].cov(down['Market']) / down['Market'].var()
    
    return {
        'up_beta': up_beta,
        'down_beta': down_beta
    }
