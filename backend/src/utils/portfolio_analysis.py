"""
Author: @Michael Laret
=====================================================================
Portfolio Analysis Module

Purpose:
Provides functions for portfolio analysis including holdings retrieval,
metrics calculation, correlation analysis, and diversification analysis.

Role in Program:
Centralized portfolio analysis functions moved from PortfolioData.py
for better organization and to eliminate duplicated code.
"""

import numpy as np
import pandas as pd
from scipy import stats
import re
import io
import sys
from contextlib import redirect_stdout, nullcontext
import json
from typing import List, Dict, Any, Optional, Tuple

# Import existing utility functions
from backend.src.utils.financial_calculations import (
    calculate_volatility,
    calculate_beta,
    calculate_var,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    get_annualization_factor,
    calculate_parametric_var,
    calculate_alpha,
    calculate_calmar_ratio,
    calculate_total_return,
    calculate_annualized_return
)
from backend.src.utils.data_retrieval import get_price_data


def get_portfolio_holdings(user_id=None, email=None):
    """
    Retrieve and format portfolio holdings from the database.
    
    Gets portfolio positions from the database and formats them into
    structured data.
    
    Args:
        user_id: The user ID to retrieve holdings for.
        email: The email to retrieve holdings for.
        
    Returns:
        List[Dict]: A list of formatted position dictionaries, or None if retrieval fails.
    """
    from backend.src.utils.retrieve_portfolio_from_db import get_holdings_from_database
    
    # Get portfolio data from database
    try:
        positions, _ = get_holdings_from_database(user_id=user_id, email=email)
        
        if not positions:
            return None
        
        # Convert database positions to expected format for compatibility
        formatted_positions = []
        for position in positions:
            # Create a simple contract-like object
            contract_obj = type('obj', (object,), {'symbol': position['symbol']})
            
            formatted_position = {
                'contract': contract_obj,
                'position': position['position'],
                'marketPrice': position['marketPrice'],
                'marketValue': position['marketValue'],
                'averageCost': position['averageCost'],
                'unrealizedPNL': position['unrealizedPNL'],
                'realizedPNL': position['realizedPNL'],
                'account': position['account']
            }
            formatted_positions.append(formatted_position)
                    
        return formatted_positions
        
    except Exception as e:
        print(f"⛔ Error retrieving portfolio: {e}")
        return None

def calculate_portfolio_metrics(symbols):
    """
    Calculate comprehensive performance metrics for a portfolio of stocks.
    
    Computes return, risk, and benchmark-relative metrics for the portfolio,
    including individual stock analysis and correlation with market indices.
    
    Args:
        symbols: List of stock symbols in the portfolio.
        
    Returns:
        Dict: Dictionary containing calculated portfolio and individual stock metrics.
    """
    # Try to get portfolio positions from database
    positions = None

    if positions is None:
        try:
            from backend.src.utils.retrieve_portfolio_from_db import retrieve_user_current_portfolio
            # This would need user_id and email parameters, but for now we'll skip database fallback
            # in portfolio metrics calculation as it requires those parameters
            positions = None
        except:
            positions = None
    
    # Define time period for analysis
    duration = '2 Y'
    bar_size = '1 day'
    
    # Get price data for all portfolio symbols using get_price_data
    price_data = {}
    for symbol in symbols:
        # Convert duration to years for get_price_data
        years = 2.0  # 2 years
        df = get_price_data(symbol, frequency='daily', years=years)
        if df is not None and not df.empty:
            # Ensure proper date index
            if 'date' in df.columns:
                df.set_index('date', inplace=True)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            price_data[symbol] = df['close']
    
    # Get market index (SPY) data for benchmark
    market_df = get_price_data('SPY', frequency='daily', years=2.0)
    market_prices = None
    if market_df is not None and not market_df.empty:
        if 'date' in market_df.columns:
            market_df.set_index('date', inplace=True)
        if not isinstance(market_df.index, pd.DatetimeIndex):
            market_df.index = pd.to_datetime(market_df.index)
        market_prices = market_df['close']
    
    # Convert price data to DataFrame and calculate returns
    all_prices = pd.DataFrame(price_data)
    returns_df = all_prices.pct_change(fill_method=None).dropna(how='all')
    
    # Calculate market returns
    market_returns = market_prices.pct_change(fill_method=None).dropna() if market_prices is not None else None
    
    # Determine portfolio weights (use actual weights if positions exist, otherwise equal)
    if positions:
        # Create weights dictionary based on market value
        weights = {p['contract'].symbol: p['marketValue'] for p in positions 
                  if p['contract'].symbol in returns_df.columns}
        total_value = sum(weights.values())
        
        if total_value > 0:
            weights = {k: v / total_value for k, v in weights.items()}
            weight_method = "position"
        else:
            weights = {symbol: 1/len(returns_df.columns) for symbol in returns_df.columns}
            weight_method = "equal"
    else:
        weights = {symbol: 1/len(returns_df.columns) for symbol in returns_df.columns}
        weight_method = "equal"
    
    # Calculate portfolio returns using weights
    portfolio_returns = pd.Series(0, index=returns_df.index)
    for symbol in returns_df.columns:
        if symbol in weights:
            portfolio_returns += returns_df[symbol].fillna(0) * weights.get(symbol, 0)
    
    # Calculate portfolio cumulative returns
    cumulative_returns = (1 + portfolio_returns).cumprod()
    
    # Get annualization factors
    periods_per_year, sqrt_periods = get_annualization_factor(bar_size)
    
    # Calculate portfolio value
    portfolio_value = sum(p['marketValue'] for p in positions) if positions else 1
    
    # Calculate all metrics
    metrics = {
        'total_return': calculate_total_return(portfolio_returns),
        'annualized_return': calculate_annualized_return(portfolio_returns, periods_per_year),
        'volatility': np.std(portfolio_returns, ddof=1) * sqrt_periods,
        'max_drawdown': calculate_max_drawdown(cumulative_returns),
    }
    
    # Add market-relative metrics if market data available
    if market_returns is not None:
        beta = calculate_beta(portfolio_returns, market_returns)
        metrics.update({
            'beta': beta,
            'alpha': calculate_alpha(portfolio_returns, market_returns, 0.03, beta),
            'market_total_return': calculate_total_return(market_returns),
            'market_annualized_return': calculate_annualized_return(market_returns, periods_per_year),
        })
    
    # Add risk metrics
    var_pct, var_amount = calculate_var(portfolio_returns, 0.99, portfolio_value)
    param_var_pct, param_var_amount = calculate_parametric_var(portfolio_returns, 0.99, portfolio_value)
    
    metrics.update({
        'historical_var_pct': var_pct,
        'historical_var_amount': var_amount,
        'parametric_var_pct': param_var_pct,
        'parametric_var_amount': param_var_amount,
        'sharpe_ratio': calculate_sharpe_ratio(portfolio_returns, 0.03, True, periods_per_year),
        'sortino_ratio': calculate_sortino_ratio(portfolio_returns, 0.03, True, periods_per_year),
        'calmar_ratio': calculate_calmar_ratio(portfolio_returns, metrics['max_drawdown'], periods_per_year),
    })
    
    # Calculate individual stock metrics
    stock_metrics = {}
    for symbol in returns_df.columns:
        stock_returns = returns_df[symbol].dropna()
        if len(stock_returns) > 0:
            stock_metrics[symbol] = _calculate_stock_metrics(
                stock_returns, market_returns, positions, symbol, 
                periods_per_year, sqrt_periods
            )
    
    metrics['stock_metrics'] = stock_metrics
    
    return metrics

def _calculate_stock_metrics(stock_returns, market_returns, positions, symbol, periods_per_year, sqrt_periods):
    """Helper function to calculate metrics for an individual stock"""
    stock_cum_returns = (1 + stock_returns).cumprod()
    stock_beta = calculate_beta(stock_returns, market_returns) if market_returns is not None else None
    stock_max_drawdown = calculate_max_drawdown(stock_cum_returns)
    
    # Get stock value if positions exist
    stock_value = next((p['marketValue'] for p in positions 
                       if p['contract'].symbol == symbol), 1) if positions else 1
    
    var_pct, var_amount = calculate_var(stock_returns, 0.99, stock_value)
    
    metrics = {
        'total_return': calculate_total_return(stock_returns),
        'annualized_return': calculate_annualized_return(stock_returns, periods_per_year),
        'volatility': np.std(stock_returns, ddof=1) * sqrt_periods,
        'max_drawdown': stock_max_drawdown,
        'var_pct': var_pct,
        'var_amount': var_amount,
        'sharpe_ratio': calculate_sharpe_ratio(stock_returns, 0.03, True, periods_per_year),
        'sortino_ratio': calculate_sortino_ratio(stock_returns, 0.03, True, periods_per_year),
        'calmar_ratio': calculate_calmar_ratio(stock_returns, stock_max_drawdown, periods_per_year)
    }
    
    # Add beta and alpha if market data available
    if market_returns is not None and stock_beta is not None:
        metrics['beta'] = stock_beta
        metrics['alpha'] = calculate_alpha(stock_returns, market_returns, 0.03, stock_beta)
    
    return metrics

def calculate_monthly_portfolio_metrics(
    symbols: Optional[List[str]] = None, 
    user_id: Optional[str] = None, 
    email: Optional[str] = None, 
    market_symbol: str = 'SPY', 
    duration: str = '2 Y', 
    confidence_level: float = 0.99, 
    risk_free_rate: float = 0.03, 
    use_position_weights: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Calculate portfolio metrics on a monthly basis for detailed performance analysis.
    
    Breaks down portfolio performance by month, computing metrics like returns,
    volatility, and benchmark comparisons for each monthly period.
    
    Args:
        symbols: List of stock symbols. If None, holdings are fetched using user_id/email.
        user_id: User ID to fetch holdings if symbols are not provided.
        email: User email to fetch holdings if symbols are not provided.
        market_symbol: Market index symbol for comparison (default: 'SPY').
        duration: Time period for data (default: '2 Y').
        confidence_level: Confidence level for VaR calculation (default: 0.99).
        risk_free_rate: Risk-free rate for calculations (default: 0.03).
        use_position_weights: Whether to use actual position weights (default: True).
        
    Returns:
        Dict: Dictionary containing overall metrics and monthly breakdown,
        or None if insufficient data.
    """
    positions = None
    if use_position_weights or not symbols:
        if not user_id and not email:
            print("❌ Cannot determine weights without user_id or email.")
        else:
            positions = get_portfolio_holdings(user_id=user_id, email=email)

    if not symbols:
        if positions:
            symbols = [p['contract'].symbol for p in positions]
        else:
            print("❌ No symbols provided and could not retrieve portfolio holdings.")
            return None
    
    # Get daily price data for all symbols for the specified duration
    
    # Convert duration string to years
    years = 2.0 if duration == '2 Y' else 1.0
    
    all_prices = {}
    for symbol in symbols:
        try:
            df = get_price_data(symbol, frequency='daily', years=years)
            if df is not None and not df.empty:
                # Ensure the date is the index and properly formatted
                if 'date' in df.columns:
                    df.set_index('date', inplace=True)
                all_prices[symbol] = df['close']
        except Exception as e:
            pass
    
    # Get market price data
    market_df = get_price_data(market_symbol, frequency='daily', years=years)
    if market_df is None or market_df.empty:
        print(f"❌ Could not get market data for {market_symbol}")
        return None
    
    # Ensure the date is the index for market data too
    if 'date' in market_df.columns:
        market_df.set_index('date', inplace=True)
    
    market_prices = market_df['close']
    
    # Convert to DataFrame and handle missing data
    prices_df = pd.DataFrame(all_prices)
    if prices_df.empty:
        print("❌ No price data available for any symbols")
        return None
    
    # Make sure index is datetime type
    if not isinstance(prices_df.index, pd.DatetimeIndex):
        try:
            prices_df.index = pd.to_datetime(prices_df.index)
        except Exception as e:
            print(f"❌ Error converting index to datetime: {e}")
            return None
    
    # Calculate daily returns
    returns_df = prices_df.pct_change(fill_method=None).dropna(how='all')
    market_returns = market_prices.pct_change(fill_method=None).dropna()
    
    # Ensure market_returns has a datetime index
    if not isinstance(market_returns.index, pd.DatetimeIndex):
        try:
            market_returns.index = pd.to_datetime(market_returns.index)
        except Exception as e:
            print(f"❌ Error converting market returns index to datetime: {e}")
            return None
    
    # Get position weights if available
    weights = None
    if use_position_weights and positions:
        # Create weights dictionary based on market value
        weights = {p['contract'].symbol: p['marketValue'] for p in positions}
        total_value = sum(weights.values())
        
        if total_value > 0:
            weights = {k: v / total_value for k, v in weights.items()}
        else:
            weights = None
    
    # Calculate portfolio returns
    if weights is not None:
        # Filter weights to only include symbols with data
        available_symbols = set(returns_df.columns)
        filtered_weights = {k: v for k, v in weights.items() if k in available_symbols}
        
        # Normalize filtered weights to sum to 1
        total_filtered_weight = sum(filtered_weights.values())
        if total_filtered_weight > 0:
            filtered_weights = {k: v / total_filtered_weight for k, v in filtered_weights.items()}
        
        # Calculate portfolio returns using weighted average
        portfolio_returns = pd.Series(0, index=returns_df.index)
        for symbol, weight in filtered_weights.items():
            portfolio_returns = portfolio_returns + returns_df[symbol] * weight
    else:
        # Equal weighting if position weights are not available or not valid
        portfolio_returns = returns_df.mean(axis=1)
    
    # Calculate portfolio metrics for the entire period
    overall_metrics = calculate_portfolio_metrics(symbols)
    
    # Prepare monthly data - ensure indices are DatetimeIndex
    portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
    market_returns.index = pd.to_datetime(market_returns.index)
    
    portfolio_returns_monthly = pd.DataFrame(portfolio_returns)
    portfolio_returns_monthly.columns = ['returns']
    portfolio_returns_monthly['year'] = portfolio_returns_monthly.index.year
    portfolio_returns_monthly['month'] = portfolio_returns_monthly.index.month
    portfolio_returns_monthly['year_month'] = portfolio_returns_monthly.index.strftime('%Y-%m')
    
    market_returns_monthly = pd.DataFrame(market_returns)
    market_returns_monthly.columns = ['returns']
    market_returns_monthly['year'] = market_returns_monthly.index.year
    market_returns_monthly['month'] = market_returns_monthly.index.month
    market_returns_monthly['year_month'] = market_returns_monthly.index.strftime('%Y-%m')
    
    # Group returns by year-month
    grouped_portfolio = portfolio_returns_monthly.groupby('year_month')
    grouped_market = market_returns_monthly.groupby('year_month')
    
    # Get the unique year-months
    year_months = sorted(portfolio_returns_monthly['year_month'].unique())
    
    # Initialize dictionary for monthly metrics
    monthly_metrics = {}
    
    # Process each month
    for year_month in year_months:
        try:
            # Get portfolio returns for this month
            month_portfolio = grouped_portfolio.get_group(year_month)['returns']
            
            # Try to get market returns for this month
            try:
                month_market = grouped_market.get_group(year_month)['returns']
            except KeyError:
                # Handle case where market data doesn't have this month
                month_dates = month_portfolio.index
                month_market = market_returns[market_returns.index.isin(month_dates)]
            
            if len(month_portfolio) < 5:  # Skip months with very little data
                continue
            
            # Calculate metrics for this month
            month_cum_returns = (1 + month_portfolio).cumprod()
            month_market_cum_returns = (1 + month_market).cumprod()
            
            # Calculate total return for the month
            month_total_return = calculate_total_return(month_portfolio)
            month_market_return = calculate_total_return(month_market)
            
            # Calculate other metrics
            month_beta = calculate_beta(month_portfolio, month_market)
            month_volatility = calculate_volatility(month_portfolio, False)
            month_max_drawdown = calculate_max_drawdown(month_cum_returns)
            month_alpha = calculate_alpha(month_portfolio, month_market, risk_free_rate/12, month_beta)
            month_var_pct, _ = calculate_var(month_portfolio, confidence_level, 1)
            month_sharpe = calculate_sharpe_ratio(month_portfolio, risk_free_rate/12, False)
            month_sortino = calculate_sortino_ratio(month_portfolio, risk_free_rate/12, False)
            
            # Store metrics for this month
            monthly_metrics[year_month] = {
                'total_return': month_total_return,
                'market_return': month_market_return,
                'relative_performance': month_total_return - month_market_return,
                'volatility': month_volatility,
                'beta': month_beta,
                'alpha': month_alpha,
                'historical_var_pct': month_var_pct,
                'max_drawdown': month_max_drawdown,
                'sharpe_ratio': month_sharpe,
                'sortino_ratio': month_sortino,
                'trading_days': len(month_portfolio)
            }
            
        except KeyError as e:
            continue
    
    # Combine the results
    results = {
        'overall_metrics': overall_metrics,
        'monthly_metrics': monthly_metrics
    }
    
    return results

def calculate_monthly_stock_metrics(symbol, market_symbol='SPY', 
                                  duration='2 Y', confidence_level=0.99, 
                                  risk_free_rate=0.03):
    """
    Calculate monthly performance metrics for a single stock.
    
    Analyzes individual stock performance on a month-by-month basis,
    providing detailed breakdown of returns and risk metrics.
    
    Args:
        symbol: Stock symbol to analyze.
        market_symbol: Symbol for market index comparison (default: 'SPY').
        duration: Time period for data (default: '2 Y').
        confidence_level: Confidence level for VaR calculation (default: 0.99).
        risk_free_rate: Annualized risk-free rate (default: 0.03).
        
    Returns:
        Dict: Dictionary containing overall metrics and monthly breakdown,
        or None if insufficient data.
    """
    print(f"\n\n📈 APPLE (AAPL) STOCK ANALYSIS\n") if symbol == "AAPL" else print(f"\n\n📈 {symbol} STOCK ANALYSIS\n")
    
    # Convert duration to years
    years = 2.0 if duration == '2 Y' else 1.0
    
    # Get price data for the stock using get_price_data
    stock_df = get_price_data(symbol, frequency='daily', years=years)
    if stock_df is None or stock_df.empty:
        print(f"Could not get price data for {symbol}")
        return None
    
    # Get market price data
    market_df = get_price_data(market_symbol, frequency='daily', years=years)
    if market_df is None or market_df.empty:
        print(f"Could not get market data for {market_symbol}")
        return None
    
    # Ensure index is date
    if 'date' in stock_df.columns:
        stock_df.set_index('date', inplace=True)
    if 'date' in market_df.columns:
        market_df.set_index('date', inplace=True)
    
    # Make sure index is datetime type
    stock_df.index = pd.to_datetime(stock_df.index)
    market_df.index = pd.to_datetime(market_df.index)
    
    # Calculate returns
    stock_returns = stock_df['close'].pct_change(fill_method=None).dropna()
    market_returns = market_df['close'].pct_change(fill_method=None).dropna()
    
    # Ensure we have enough data
    if len(stock_returns) < 20:
        print(f"Insufficient data for {symbol} (found only {len(stock_returns)} data points)")
        return None
    
    # Calculate overall stock metrics first (this can be simplified but for consistency we'll use existing function)
    stock_metrics = {}
    
    # Create a fake portfolio with just this stock
    fake_symbols = [symbol]
    overall_metrics = calculate_portfolio_metrics(fake_symbols)
    
    # Prepare monthly data
    stock_returns_monthly = pd.DataFrame(stock_returns)
    stock_returns_monthly.columns = ['returns']
    stock_returns_monthly['year'] = stock_returns_monthly.index.year
    stock_returns_monthly['month'] = stock_returns_monthly.index.month
    stock_returns_monthly['year_month'] = stock_returns_monthly.index.strftime('%Y-%m')
    
    market_returns_monthly = pd.DataFrame(market_returns)
    market_returns_monthly.columns = ['returns']
    market_returns_monthly['year'] = market_returns_monthly.index.year
    market_returns_monthly['month'] = market_returns_monthly.index.month
    market_returns_monthly['year_month'] = market_returns_monthly.index.strftime('%Y-%m')
    
    # Group returns by year-month
    grouped_stock = stock_returns_monthly.groupby('year_month')
    grouped_market = market_returns_monthly.groupby('year_month')
    
    # Get the unique year-months
    year_months = sorted(stock_returns_monthly['year_month'].unique())
    
    # Initialize dictionary for monthly metrics
    monthly_metrics = {}
    
    # Process each month (without debug prints)
    for year_month in year_months:
        try:
            # Get stock returns for this month
            month_stock = grouped_stock.get_group(year_month)['returns']
            
            # Try to get market returns for this month
            try:
                month_market = grouped_market.get_group(year_month)['returns']
            except KeyError:
                month_dates = month_stock.index
                month_market = market_returns[market_returns.index.isin(month_dates)]
            
            if len(month_stock) < 5:  # Skip months with very little data
                continue
            
            # Calculate metrics for this month
            month_cum_returns = (1 + month_stock).cumprod()
            month_market_cum_returns = (1 + month_market).cumprod()
            
            # Calculate total return for the month
            month_total_return = calculate_total_return(month_stock)
            month_market_return = calculate_total_return(month_market)
            
            # Calculate other metrics
            month_beta = calculate_beta(month_stock, month_market)
            month_volatility = calculate_volatility(month_stock, False)
            month_max_drawdown = calculate_max_drawdown(month_cum_returns)
            month_alpha = calculate_alpha(month_stock, month_market, risk_free_rate/12, month_beta)
            month_var_pct, _ = calculate_var(month_stock, confidence_level, 1)
            month_sharpe = calculate_sharpe_ratio(month_stock, risk_free_rate/12, False)
            month_sortino = calculate_sortino_ratio(month_stock, risk_free_rate/12, False)
            
            # Store metrics for this month
            monthly_metrics[year_month] = {
                'total_return': month_total_return,
                'market_return': month_market_return,
                'relative_performance': month_total_return - month_market_return,
                'volatility': month_volatility,
                'beta': month_beta,
                'alpha': month_alpha,
                'historical_var_pct': month_var_pct,
                'max_drawdown': month_max_drawdown,
                'sharpe_ratio': month_sharpe,
                'sortino_ratio': month_sortino,
                'trading_days': len(month_stock)
            }
            
        except KeyError:
            continue
    
    # Combine the results
    results = {
        'symbol': symbol,
        'overall_metrics': overall_metrics['stock_metrics'].get(symbol, {}) if overall_metrics and 'stock_metrics' in overall_metrics else {},
        'monthly_metrics': monthly_metrics
    }
    
    return results 

def analyze_portfolio_correlations(symbols: List[str], duration: str = '2 Y', bar_size: str = '1 day') -> Optional[pd.DataFrame]:
    """
    Calculate correlation matrix for portfolio holdings.
    
    Computes pairwise correlations between portfolio stocks to assess
    diversification and identify potential concentration risks.
    
    Args:
        symbols: List of stock symbols to analyze.
        duration: Time period for data (default: '2 Y').
        bar_size: Bar size for data (default: '1 day').
        
    Returns:
        pd.DataFrame: DataFrame containing the correlation matrix, or None if analysis fails.
    """
    if not symbols:
        print("⛔ No symbols provided for correlation analysis.")
        return None

    try:
        # Get historical price data for all symbols using get_price_data
        print(f"📈 Retrieving {duration} of {bar_size} price data for {len(symbols)} symbols...")
        
        # Convert duration to years
        years = 2.0 if duration == '2 Y' else 1.0
        
        price_data = {}
        
        for symbol in symbols:
            try:
                df = get_price_data(symbol, frequency='daily', years=years)
                if df is not None and not df.empty:
                    # Ensure index is datetime
                    if not isinstance(df.index, pd.DatetimeIndex):
                        if 'date' in df.columns:
                            df.set_index('date', inplace=True)
                        df.index = pd.to_datetime(df.index)
                    
                    # Store close prices
                    price_data[symbol] = df['close']
                else:
                    pass
            except Exception as e:
                pass
        
        if not price_data:
            print("⛔ No price data retrieved for any symbols")
            return None
        
        # Convert to DataFrame
        all_prices = pd.DataFrame(price_data)
        
        # Calculate returns
        returns = all_prices.pct_change(fill_method=None).dropna()
        
        # Calculate correlation matrix
        correlation_matrix = returns.corr()
        
        return correlation_matrix
        
    except Exception as e:
        print(f"❌ Error analyzing portfolio correlations: {e}")
        return None 
