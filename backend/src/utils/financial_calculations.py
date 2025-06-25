"""
Financial calculation utility functions.
"""
import numpy as np
import pandas as pd
from scipy import stats
from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository
from datetime import datetime, timedelta

def calculate_volatility(returns, annualize=True, trading_days=252):
    """
    Calculate the volatility (standard deviation) of returns
    
    Args:
        returns: pandas Series or numpy array of returns
        annualize: whether to annualize the volatility
        trading_days: number of trading days in a year (default: 252)
        
    Returns:
        Volatility value
    """
    # Calculate standard deviation of returns
    volatility = np.std(returns, ddof=1)
    
    # Annualize if requested
    if annualize:
        # For daily returns, annualize by multiplying by sqrt(trading_days)
        volatility = volatility * np.sqrt(trading_days)
            
    return volatility

def calculate_beta(returns, market_returns):
    """
    Calculate the beta (market risk) of a portfolio or stock
    
    Args:
        returns: pandas Series or numpy array of portfolio/stock returns
        market_returns: pandas Series or numpy array of market returns (e.g. S&P 500)
        
    Returns:
        Beta value
    """
    # Convert inputs to pandas Series if they aren't already
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)
    if not isinstance(market_returns, pd.Series):
        market_returns = pd.Series(market_returns)
    
    # Ensure both series have the same index if they are pandas Series
    if hasattr(returns, 'index') and hasattr(market_returns, 'index'):
        # Find common dates
        common_index = returns.index.intersection(market_returns.index)
        
        if len(common_index) == 0:
            print("Warning: No overlapping dates between portfolio and market returns")
            return 0.0
            
        # Filter to common dates
        returns = returns.loc[common_index]
        market_returns = market_returns.loc[common_index]
    
    # If they're numpy arrays, ensure they have the same length
    elif len(returns) != len(market_returns):
        # Use the shorter length
        min_length = min(len(returns), len(market_returns))
        returns = returns[:min_length]
        market_returns = market_returns[:min_length]
        print(f"Warning: Returns series have different lengths. Using first {min_length} elements.")
    
    # Calculate covariance between portfolio and market
    covariance = np.cov(returns, market_returns)[0, 1]
    
    # Calculate market variance
    market_variance = np.var(market_returns, ddof=1)
    
    # Calculate beta
    beta = covariance / market_variance
    
    return beta

def calculate_var(returns, confidence_level=0.95, amount=1):
    """
    Calculate Value at Risk (VaR) using historical simulation method
    
    Args:
        returns: pandas Series or numpy array of returns
        confidence_level: desired confidence level (default: 0.95 for 95%)
        amount: investment amount to calculate VaR in currency terms
        
    Returns:
        VaR value as a percentage and in currency terms (if amount provided)
    """
    # Sort returns
    sorted_returns = np.sort(returns)
    
    # Find the index at the specified confidence level
    index = int(len(sorted_returns) * (1 - confidence_level))
    
    # Get the return at that index (VaR as a percentage)
    var_pct = abs(sorted_returns[index])
    
    # Calculate VaR in currency terms if amount is provided
    var_amount = var_pct * amount
    
    return var_pct, var_amount

def calculate_max_drawdown(cumulative_returns):
    """
    Calculate Maximum Drawdown
    
    Args:
        cumulative_returns: pandas Series or numpy array of cumulative returns
        
    Returns:
        Maximum Drawdown value as a percentage
    """
    # Calculate running maximum
    running_max = np.maximum.accumulate(cumulative_returns)
    
    # Calculate drawdown
    drawdown = (cumulative_returns - running_max) / running_max
    
    # Find maximum drawdown
    max_drawdown = abs(np.min(drawdown))
    
    return max_drawdown

def calculate_sharpe_ratio(returns, risk_free_rate=0.0, annualize=True, trading_days=252):
    """
    Calculate Sharpe Ratio
    
    Args:
        returns: pandas Series or numpy array of returns
        risk_free_rate: annualized risk-free rate (default: 0.0)
        annualize: whether to annualize the returns and volatility
        trading_days: number of trading days in a year (default: 252)
        
    Returns:
        Sharpe Ratio value
    """
    # Calculate average return
    avg_return = np.mean(returns)
    
    # Calculate volatility
    volatility = np.std(returns, ddof=1)
    
    # Adjust for annualization if requested
    if annualize:
        # Adjust daily values to annual values
        avg_return = avg_return * trading_days
        volatility = volatility * np.sqrt(trading_days)
        # risk_free_rate is assumed to be already annualized
    else:
        # Convert annual risk-free rate to daily
        risk_free_rate = risk_free_rate / trading_days
    
    # Calculate Sharpe ratio
    if volatility == 0: # Avoid division by zero
        return 0.0 if avg_return - risk_free_rate == 0 else float('inf') * np.sign(avg_return - risk_free_rate)
    sharpe_ratio = (avg_return - risk_free_rate) / volatility
    
    return sharpe_ratio

def calculate_sortino_ratio(returns, risk_free_rate=0.0, annualize=True, trading_days=252):
    """
    Calculate Sortino Ratio - similar to Sharpe but only penalizes downside volatility
    
    Args:
        returns: pandas Series or numpy array of returns
        risk_free_rate: annualized risk-free rate (default: 0.0)
        annualize: whether to annualize the returns and volatility
        trading_days: number of trading days in a year (default: 252)
        
    Returns:
        Sortino Ratio value
    """
    # Calculate average return
    avg_return = np.mean(returns)
    
    # Calculate downside returns - only negative returns
    downside_returns = returns[returns < 0]
    
    # Calculate downside deviation (downside risk)
    # If no negative returns, return a large number
    if len(downside_returns) == 0:
        return float('inf') if avg_return - risk_free_rate > 0 else (0.0 if avg_return - risk_free_rate == 0 else float('-inf'))
    
    downside_deviation = np.sqrt(np.mean(downside_returns**2))
    if downside_deviation == 0: # Avoid division by zero
        return float('inf') if avg_return - risk_free_rate > 0 else (0.0 if avg_return - risk_free_rate == 0 else float('-inf'))

    # Adjust for annualization if requested
    if annualize:
        # Adjust daily values to annual values
        avg_return = avg_return * trading_days
        downside_deviation = downside_deviation * np.sqrt(trading_days)
        # risk_free_rate is assumed to be already annualized
    else:
        # Convert annual risk-free rate to daily
        risk_free_rate = risk_free_rate / trading_days
    
    # Calculate Sortino ratio
    sortino_ratio = (avg_return - risk_free_rate) / downside_deviation
    
    return sortino_ratio

def get_annualization_factor(bar_size):
    """
    Determine the annualization factor based on the bar size
    
    Args:
        bar_size: Bar size for data (e.g., '1 day', '1 hour', '1 min', '1W', '1M')
        
    Returns:
        Tuple of (periods_per_year, sqrt_periods_per_year) for return and volatility annualization
    """
    # Lower case for consistent comparison
    bar_size = bar_size.lower()
    
    if 'min' in bar_size or 'mins' in bar_size:
        # Minutes - assuming trading day has 6.5 hours = 390 minutes
        minutes = int(bar_size.split()[0])
        periods_per_day = 390 / minutes
        periods_per_year = periods_per_day * 252
    elif 'hour' in bar_size or 'hours' in bar_size:
        # Hours - assuming trading day has 6.5 hours
        hours = int(bar_size.split()[0])
        periods_per_day = 6.5 / hours
        periods_per_year = periods_per_day * 252
    elif 'day' in bar_size:
        # Daily data
        periods_per_year = 252
    elif 'week' in bar_size or 'w' in bar_size:
        # Weekly data
        periods_per_year = 52
    elif 'month' in bar_size or 'm' in bar_size:
        # Monthly data
        periods_per_year = 12
    else:
        # Default to daily if unknown
        periods_per_year = 252
    
    return periods_per_year, np.sqrt(periods_per_year)

def calculate_parametric_var(returns, confidence_level=0.99, amount=1):
    """
    Calculate Value at Risk (VaR) using parametric method (assuming normal distribution)
    
    Args:
        returns: pandas Series or numpy array of returns
        confidence_level: desired confidence level (default: 0.99 for 99%)
        amount: investment amount to calculate VaR in currency terms
        
    Returns:
        VaR value as a percentage and in currency terms
    """
    # Calculate mean and standard deviation of returns
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    # Get z-score for the confidence level
    z_score = stats.norm.ppf(confidence_level)
    
    # Calculate parametric VaR
    var_pct = abs(mean_return - z_score * std_return)
    var_amount = var_pct * amount
    
    return var_pct, var_amount

def calculate_alpha(returns, market_returns, risk_free_rate, beta=None):
    """
    Calculate Alpha - excess return of investment relative to a benchmark
    
    Args:
        returns: pandas Series or numpy array of portfolio returns
        market_returns: pandas Series or numpy array of market returns
        risk_free_rate: risk-free rate (annualized)
        beta: pre-calculated beta (if None, will be calculated)
        
    Returns:
        Alpha value
    """
    # Make sure we're working with common dates or lengths
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)
    if not isinstance(market_returns, pd.Series):
        market_returns = pd.Series(market_returns)
    
    # Align dates if series have indexes
    if hasattr(returns, 'index') and hasattr(market_returns, 'index'):
        common_index = returns.index.intersection(market_returns.index)
        if len(common_index) > 0:
            returns = returns.loc[common_index]
            market_returns = market_returns.loc[common_index]
        elif len(common_index) == 0 and len(returns) > 0 and len(market_returns) > 0 : # if no common index but data exists
            print("Warning: No common dates between portfolio and market returns. Alpha might be misleading.")
    
    # Calculate average returns
    avg_portfolio_return = np.mean(returns) * 252  # Annualize
    avg_market_return = np.mean(market_returns) * 252  # Annualize
    
    # Get or calculate beta
    if beta is None:
        beta = calculate_beta(returns, market_returns)
    
    # Daily risk-free rate (assuming risk_free_rate is annual)
    # Ensure risk_free_rate is float, default to 0 if None
    risk_free_rate_float = float(risk_free_rate) if risk_free_rate is not None else 0.0
    daily_rf = risk_free_rate_float / 252
    
    # Alpha calculation (CAPM formula)
    alpha = avg_portfolio_return - (daily_rf * 252 + beta * (avg_market_return - daily_rf * 252))
    
    return alpha

def calculate_calmar_ratio(returns, max_drawdown, trading_days=252):
    """
    Calculate Calmar Ratio (return / maximum drawdown)
    
    Args:
        returns: pandas Series or numpy array of returns
        max_drawdown: maximum drawdown value
        trading_days: number of trading days in a year (default: 252)
        
    Returns:
        Calmar Ratio value
    """
    if max_drawdown == 0:
        return float('inf')  # Avoid division by zero
    
    # Calculate annualized return
    avg_return = np.mean(returns)
    annualized_return = avg_return * trading_days
    
    # Calculate Calmar ratio
    calmar_ratio = annualized_return / max_drawdown
    
    return calmar_ratio

def calculate_total_return(returns):
    """
    Calculate total return over a period from a series of returns
    
    Args:
        returns: pandas Series or numpy array of returns
        
    Returns:
        Total return as a percentage
    """
    # Calculate total return using compounding
    if not isinstance(returns, (pd.Series, np.ndarray)) or len(returns) == 0:
        return 0.0
    total_return = (1 + returns).prod() - 1
    return total_return

def calculate_annualized_return(returns, period=252):
    """
    Calculate annualized return from a series of returns
    
    Args:
        returns: pandas Series or numpy array of returns
        period: number of periods in a year (default: 252 for daily data)
        
    Returns:
        Annualized return as a percentage
    """
    # Calculate total return
    total_return = calculate_total_return(returns)
    
    # Annualize the return
    n_periods = len(returns)
    if n_periods == 0:
        return 0.0
    
    years = n_periods / period
    if years == 0: # Avoid division by zero if less than one period
        return total_return # Return total return if period is less than a year's worth of data
        
    annualized_return = (1 + total_return) ** (1 / years) - 1
    
    return annualized_return

def calculate_treynor_ratio(returns, market_returns=None, risk_free_rate=0.0, beta=None, annualize=True, trading_days=252):
    """
    Calculate the Treynor Ratio – excess return per unit of systematic risk (beta).

    Args:
        returns: pandas Series or numpy array of portfolio/stock returns (daily)
        market_returns: pandas Series or numpy array of benchmark returns; required if *beta* is not supplied
        risk_free_rate: annualised risk-free rate (default 0.0)
        beta: optional pre-computed beta; if None it will be calculated from the supplied returns
        annualize: whether to annualise the numerator (and risk-free adjustment)
        trading_days: number of periods per year (default 252 for daily data)

    Returns:
        Treynor ratio value. Returns 0 if beta is 0 or cannot be computed.
    """
    if beta is None:
        if market_returns is None:
            print("Warning: Treynor ratio needs either beta or market_returns. Returning 0.")
            return 0.0
        beta = calculate_beta(returns, market_returns)

    # Protect against divide-by-zero
    if beta == 0 or beta is None:
        return 0.0

    avg_return = np.mean(returns)
    if annualize:
        avg_return *= trading_days
        # risk_free_rate assumed annual
    else:
        risk_free_rate = risk_free_rate / trading_days

    treynor_ratio = (avg_return - risk_free_rate) / beta
    return treynor_ratio

def calculate_information_ratio(returns, benchmark_returns, annualize=True, trading_days=252):
    """
    Calculate the Information Ratio – active return divided by tracking error.

    Args:
        returns: pandas Series or numpy array of portfolio/stock returns (daily)
        benchmark_returns: pandas Series or numpy array of benchmark returns (daily)
        annualize: whether to annualise (default True)
        trading_days: periods per year (default 252)

    Returns:
        Information ratio value. Returns 0 if tracking error is 0 or cannot be computed.
    """
    if returns is None or benchmark_returns is None:
        return 0.0

    # Ensure same length/index
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns)
    if not isinstance(benchmark_returns, pd.Series):
        benchmark_returns = pd.Series(benchmark_returns)

    common_idx = returns.index.intersection(benchmark_returns.index)
    if len(common_idx) == 0:
        # Fallback to element-wise min length
        min_len = min(len(returns), len(benchmark_returns))
        returns = returns.iloc[:min_len]
        benchmark_returns = benchmark_returns.iloc[:min_len]
    else:
        returns = returns.loc[common_idx]
        benchmark_returns = benchmark_returns.loc[common_idx]

    active_returns = returns - benchmark_returns
    tracking_error = np.std(active_returns, ddof=1)
    if annualize:
        active_return = np.mean(active_returns) * trading_days
        tracking_error *= np.sqrt(trading_days)
    else:
        active_return = np.mean(active_returns)

    if tracking_error == 0:
        return 0.0

    info_ratio = active_return / tracking_error
    return info_ratio 

# CHANGE DATA RETRIEVAL FUNCTION
def get_returns(symbols, duration='1 Y'):
    """
    Get historical returns for portfolio stocks.
    
    Retrieves price data for multiple symbols and calculates their returns,
    handling missing data gracefully.
    
    Args:
        symbols: List of stock symbols.
        duration: Time period for data (default: '1 Y').
        
    Returns:
        pd.DataFrame: DataFrame with returns for all symbols, or None if no data available.
    """
    all_data = {}
    missing_data = []

    try:
        years = float(duration.split(' ')[0])
    except (ValueError, IndexError):
        years = 1.0
    
    for symbol in symbols:
        try:
            df = EquityPriceDataRepository().fetch_equity_price_data(symbol, start_date=datetime.now() - timedelta(days=1460), end_date=datetime.now(), interval='1D')
            
            if df is not None and not df.empty:
                if 'date' in df.columns:
                    df.set_index('date', inplace=True)
                
                # Calculate returns
                returns = df['close'].pct_change().dropna()
                all_data[symbol] = returns
            else:
                missing_data.append(symbol)
                
        except Exception as e:
            print(f"Error getting data for {symbol}: {e}")
            missing_data.append(symbol)
    
    if missing_data:
        print(f"Warning: Missing historical data for symbols: {', '.join(missing_data)}")
            
    # Create a DataFrame with all returns
    if all_data:
        returns_df = pd.DataFrame(all_data)
        # Drop rows with all NaNs
        returns_df = returns_df.dropna(how='all')
        return returns_df
    
    return None

if __name__ == "__main__":
    symbols = ["AAPL"]
    returns = get_returns(symbols, duration="3 Y")
    max_drawdown = calculate_max_drawdown(returns)
    print(calculate_calmar_ratio(returns, max_drawdown))
    print(returns)