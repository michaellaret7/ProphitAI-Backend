import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from backend.src.calculations.returns_calculations.portfolio_returns_calculations import CalculatePortfolioReturns
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers

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

#TODO: move this to a better place and revamp this file
def get_upside_downside_ratios(portfolio_dict: dict):
    """
    Calculate up and down capture ratios for portfolio and individual tickers.

    Parameters:
    - portfolio_dict: Dictionary with tickers as keys and 'conviction'/'position' as values
    - benchmark_ticker: Benchmark ticker to compare against (default: SPY)

    Returns:
    - dict: Contains portfolio and individual ticker up/down capture ratios
    """
    benchmark_ticker = 'SPY'

    # Calculate date range (last 252 trading days, approximately 1 year)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=252)

    # Convert to string format expected by fetch_bulk_price_data_for_tickers
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Get all tickers including benchmark
    tickers = list(portfolio_dict.keys()) + [benchmark_ticker]

    # Fetch price data
    price_data = fetch_bulk_price_data_for_tickers(tickers, start_date_str, end_date_str, frequency='daily')

    if not price_data or benchmark_ticker not in price_data:
        print(f"Unable to fetch price data for benchmark {benchmark_ticker}")
        return None

    # Create DataFrame from price data
    prices_df = pd.DataFrame(price_data)

    # Calculate daily returns
    returns = prices_df.pct_change(fill_method=None).dropna()

    # Separate benchmark returns
    benchmark_returns = returns[benchmark_ticker]

    # Identify up and down market periods
    up_market = benchmark_returns > 0
    down_market = benchmark_returns < 0

    # Initialize results dictionary
    results = {
        'up_capture': {},
        'down_capture': {}
    }

    # Calculate capture ratios for each ticker
    for ticker in portfolio_dict.keys():
        if ticker not in returns.columns:
            continue
            
        # Get ticker returns
        ticker_returns = returns[ticker]
        
        # Adjust returns for short positions
        if portfolio_dict[ticker]['position'] == 'short':
            ticker_returns = -ticker_returns
        
        # Calculate up-market capture
        ticker_up_returns = ticker_returns[up_market].mean()
        benchmark_up_returns = benchmark_returns[up_market].mean()
        up_capture = (ticker_up_returns / benchmark_up_returns * 100) if benchmark_up_returns != 0 else np.nan
        
        # Calculate down-market capture
        ticker_down_returns = ticker_returns[down_market].mean()
        benchmark_down_returns = benchmark_returns[down_market].mean()
        down_capture = (ticker_down_returns / benchmark_down_returns * 100) if benchmark_down_returns != 0 else np.nan
        
        results['up_capture'][ticker] = round(float(up_capture), 3)
        results['down_capture'][ticker] = round(float(down_capture), 3)

    # Calculate portfolio-level capture ratios
    portfolio_returns = pd.Series(0.0, index=returns.index)

    for ticker, details in portfolio_dict.items():
        if ticker not in returns.columns:
            continue
        
        weight = details['conviction']
        position = details['position']
        
        # Adjust returns for position type
        if position == 'long':
            portfolio_returns += returns[ticker] * weight
        else:  # short
            portfolio_returns -= returns[ticker] * weight

    # Portfolio up-market capture
    portfolio_up_returns = portfolio_returns[up_market].mean()
    portfolio_up_capture = (portfolio_up_returns / benchmark_up_returns * 100) if benchmark_up_returns != 0 else np.nan

    # Portfolio down-market capture
    portfolio_down_returns = portfolio_returns[down_market].mean()
    portfolio_down_capture = (portfolio_down_returns / benchmark_down_returns * 100) if benchmark_down_returns != 0 else np.nan

    results['portfolio_up_capture'] = round(float(portfolio_up_capture), 3)
    results['portfolio_down_capture'] = round(float(portfolio_down_capture), 3)

    return results