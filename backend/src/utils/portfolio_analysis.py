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
from datetime import datetime, timedelta
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
from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository
from backend.src.repositories.user.user_portfolio_repository import UserCurrentPortfolioRepository

def _fetch_price_data_for_analysis(
    symbols: List[str], 
    market_symbol: str = 'SPY', 
    years: float = 2.0
) -> Tuple[Optional[pd.DataFrame], Optional[pd.Series]]:
    """
    Fetches price data for a list of symbols and a market benchmark.
    This is a helper function to avoid redundant data fetching in analysis functions.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(365.25 * years))

    all_prices = {}
    for symbol in symbols:
        df = EquityPriceDataRepository().fetch_equity_price_data(
            symbol, start_date=start_date, end_date=end_date, interval='1D'
        )
        if df is not None and not df.empty:
            if 'date' in df.columns:
                df.set_index('date', inplace=True)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            all_prices[symbol] = df['close']

    if not all_prices:
        return None, None
        
    prices_df = pd.DataFrame(all_prices)

    market_df = ETFPriceDataRepository().fetch_etf_price_data(
        market_symbol, start_date=start_date, end_date=end_date, interval='1D'
    )
    market_prices = None
    if market_df is not None and not market_df.empty:
        if 'date' in market_df.columns:
            market_df.set_index('date', inplace=True)
        if not isinstance(market_df.index, pd.DatetimeIndex):
            market_df.index = pd.to_datetime(market_df.index)
        market_prices = market_df['close']
        
    return prices_df, market_prices

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
    # Get portfolio data from database
    try:
        positions = UserCurrentPortfolioRepository().fetch_holdings(user_id=user_id, email=email)
        
        if not positions:
            return None
        
        # Convert database positions to expected format for compatibility
        formatted_positions = []
        for position in positions:
            # Create a simple contract-like object
            contract_obj = type('obj', (object,), {'symbol': position.symbol})
            
            formatted_position = {
                'contract': contract_obj,
                'position': position.position,
                'marketPrice': position.marketprice,
                'marketValue': position.marketvalue,
                'averageCost': position.averagecost,
                'unrealizedPNL': position.unrealizedpnl,
                'realizedPNL': position.realizedpnl,
                'account': position.account
            }
            formatted_positions.append(formatted_position)
                    
        return formatted_positions
        
    except Exception as e:
        print(f"⛔ Error retrieving portfolio: {e}")
        return None

def calculate_portfolio_metrics(
    prices_df: pd.DataFrame,
    market_prices: pd.Series,
    positions: Optional[List[Dict]] = None,
    bar_size: str = '1 day'
) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics for a portfolio of stocks.
    
    Computes return, risk, and benchmark-relative metrics for the portfolio,
    including individual stock analysis and correlation with market indices.
    
    Args:
        prices_df: DataFrame of historical prices for portfolio symbols.
        market_prices: Series of historical prices for the market benchmark.
        positions: Optional list of portfolio positions for weighting.
        bar_size: The bar size of the data, for annualization factors.
        
    Returns:
        Dict: Dictionary containing calculated portfolio and individual stock metrics.
    """
    returns_df = prices_df.pct_change(fill_method=None).dropna(how='all')
    market_returns = market_prices.pct_change(fill_method=None).dropna() if market_prices is not None else None
    
    if positions:
        weights = {p['contract'].symbol: p['marketValue'] for p in positions if p['contract'].symbol in returns_df.columns}
        total_value = sum(weights.values())
        if total_value > 0:
            weights = {k: v / total_value for k, v in weights.items()}
        else:
            weights = {symbol: 1/len(returns_df.columns) for symbol in returns_df.columns}
    else:
        weights = {symbol: 1/len(returns_df.columns) for symbol in returns_df.columns}
    
    portfolio_returns = pd.Series(0, index=returns_df.index)
    for symbol in returns_df.columns:
        if symbol in weights:
            portfolio_returns += returns_df[symbol].fillna(0) * weights.get(symbol, 0)
    
    cumulative_returns = (1 + portfolio_returns).cumprod()
    periods_per_year, sqrt_periods = get_annualization_factor(bar_size)
    portfolio_value = sum(p['marketValue'] for p in positions) if positions else 1
    
    metrics = {
        'total_return': calculate_total_return(portfolio_returns),
        'annualized_return': calculate_annualized_return(portfolio_returns, periods_per_year),
        'volatility': np.std(portfolio_returns, ddof=1) * sqrt_periods,
        'max_drawdown': calculate_max_drawdown(cumulative_returns),
    }
    
    if market_returns is not None:
        beta = calculate_beta(portfolio_returns, market_returns)
        metrics.update({
            'beta': beta,
            'alpha': calculate_alpha(portfolio_returns, market_returns, 0.03, beta),
            'market_total_return': calculate_total_return(market_returns),
            'market_annualized_return': calculate_annualized_return(market_returns, periods_per_year),
        })
    
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
    prices_df: pd.DataFrame,
    market_prices: pd.Series,
    positions: Optional[List[Dict]] = None,
    confidence_level: float = 0.99, 
    risk_free_rate: float = 0.03, 
    use_position_weights: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Calculate portfolio metrics on a monthly basis for detailed performance analysis.
    
    Breaks down portfolio performance by month, computing metrics like returns,
    volatility, and benchmark comparisons for each monthly period.
    
    Args:
        prices_df: DataFrame of historical prices for portfolio symbols.
        market_prices: Series of historical prices for the market benchmark.
        positions: Optional list of portfolio positions for weighting.
        confidence_level: Confidence level for VaR calculation (default: 0.99).
        risk_free_rate: Risk-free rate for calculations (default: 0.03).
        use_position_weights: Whether to use actual position weights (default: True).
        
    Returns:
        Dict: Dictionary containing a monthly breakdown of metrics,
        or None if insufficient data.
    """
    if prices_df is None or prices_df.empty:
        print("❌ No price data available for any symbols")
        return None
        
    returns_df = prices_df.pct_change(fill_method=None).dropna(how='all')
    market_returns = market_prices.pct_change(fill_method=None).dropna()
    
    weights = None
    if use_position_weights and positions:
        weights = {p['contract'].symbol: p['marketValue'] for p in positions}
        total_value = sum(weights.values())
        if total_value > 0:
            weights = {k: v / total_value for k, v in weights.items()}
        else:
            weights = None
    
    if weights is not None:
        available_symbols = set(returns_df.columns)
        filtered_weights = {k: v for k, v in weights.items() if k in available_symbols}
        total_filtered_weight = sum(filtered_weights.values())
        if total_filtered_weight > 0:
            filtered_weights = {k: v / total_filtered_weight for k, v in filtered_weights.items()}
        
        portfolio_returns = pd.Series(0, index=returns_df.index)
        for symbol, weight in filtered_weights.items():
            portfolio_returns = portfolio_returns + returns_df[symbol].fillna(0) * weight
    else:
        portfolio_returns = returns_df.mean(axis=1)
    
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
    
    grouped_portfolio = portfolio_returns_monthly.groupby('year_month')
    grouped_market = market_returns_monthly.groupby('year_month')
    
    year_months = sorted(portfolio_returns_monthly['year_month'].unique())
    
    monthly_metrics = {}
    
    for year_month in year_months:
        try:
            month_portfolio = grouped_portfolio.get_group(year_month)['returns']
            
            try:
                month_market = grouped_market.get_group(year_month)['returns']
            except KeyError:
                month_dates = month_portfolio.index
                month_market = market_returns[market_returns.index.isin(month_dates)]
            
            if len(month_portfolio) < 5:
                continue
            
            month_cum_returns = (1 + month_portfolio).cumprod()
            
            month_total_return = calculate_total_return(month_portfolio)
            month_market_return = calculate_total_return(month_market)
            
            month_beta = calculate_beta(month_portfolio, month_market)
            month_volatility = calculate_volatility(month_portfolio, False)
            month_max_drawdown = calculate_max_drawdown(month_cum_returns)
            month_alpha = calculate_alpha(month_portfolio, month_market, risk_free_rate/12, month_beta)
            month_var_pct, _ = calculate_var(month_portfolio, confidence_level, 1)
            month_sharpe = calculate_sharpe_ratio(month_portfolio, risk_free_rate/12, False)
            month_sortino = calculate_sortino_ratio(month_portfolio, risk_free_rate/12, False)
            
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
    
    return monthly_metrics

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
    
    stock_df = EquityPriceDataRepository().fetch_equity_price_data(symbol, start_date=datetime.now() - timedelta(days=1460), end_date=datetime.now(), interval='1D')
    if stock_df is None or stock_df.empty:
        print(f"Could not get price data for {symbol}")
        return None
    
    # Get market price data
    market_df = ETFPriceDataRepository().fetch_etf_price_data(market_symbol, start_date=datetime.now() - timedelta(days=1460), end_date=datetime.now(), interval='1D')
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
    overall_metrics = calculate_portfolio_metrics(stock_df, market_returns, positions=[{'contract': type('obj', (object,), {'symbol': symbol}), 'marketValue': 1}], bar_size='1 day')
    
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

def analyze_portfolio_correlations(prices_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Calculate correlation matrix for portfolio holdings.
    
    Computes pairwise correlations between portfolio stocks to assess
    diversification and identify potential concentration risks.
    
    Args:
        prices_df: DataFrame of historical prices for portfolio symbols.
        
    Returns:
        pd.DataFrame: DataFrame containing the correlation matrix, or None if analysis fails.
    """
    if prices_df is None or prices_df.empty:
        print("⛔ No price data provided for correlation analysis.")
        return None

    try:
        returns = prices_df.pct_change(fill_method=None).dropna()
        correlation_matrix = returns.corr()
        return correlation_matrix
        
    except Exception as e:
        print(f"❌ Error analyzing portfolio correlations: {e}")
        return None 
