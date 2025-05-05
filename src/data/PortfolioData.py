"""
Author: @Michael Laret
=====================================================================
Portfolio Data & Analysis Module

Purpose:
Connects to IBKR to fetch portfolio/market data (holdings, prices) and perform
financial analysis (metrics, diversification, correlations).

Role in Program:
Provides IBKR data and analysis for portfolio monitoring, risk assessment,
and performance reporting.
"""
from ib_insync import IB, Stock, util
import numpy as np
import pandas as pd
from scipy import stats
import re
import io
import sys
from contextlib import redirect_stdout, nullcontext

def connect_to_ib():
    """
    Establish a connection to Interactive Brokers TWS or Gateway
    
    Attempts to connect on standard ports (4002, 7497) with different client IDs.
    
    Returns:
        IB connection object if successful, None if connection fails
    """
    ib = IB()
    
    # Disconnect if already connected
    if ib.isConnected():
        ib.disconnect()

    connected = False
    
    # Try standard TWS/Gateway ports
    ports = [4002, 7497]  # 4002 for Gateway, 7497 for TWS
    
    for port in ports:
        for client_id in range(7):  # Try client IDs from 0 to 6
            try:
                ib.connect('127.0.0.1', port, clientId=client_id)
                connected = True
                print(f"🌐 Connected to IB on port {port} with client ID {client_id}")
                return ib
            except Exception as e:
                print(f"🚨 Connection failed on port {port} with client ID {client_id}: {e}")
    
    print("⛔ Could not connect to IB on any port or client ID")
    return None

def get_historical_price_data(ib, symbol, duration='1 D', bar_size='1 min', date=None):
    """
    Get historical price data for a given stock symbol
    
    Args:
        ib: IB connection
        symbol: Stock symbol to get data for
        duration: Time period for data (default: '1 D')
        bar_size: Bar size for data (default: '1 min')
        date: Specific end date for data (default: None, which means latest data)
        
    Returns:
        DataFrame containing historical price data
    """
    contract = Stock(symbol, 'SMART', 'USD')
    try:
        qualified_contract = ib.qualifyContracts(contract)[0]
    except:
        return None

    # Format date if provided
    if date is not None:
        if '-' in date:
            date = date.replace('-', '')
        date = date + ' 16:00:00'
    else:
        date = ''

    # Request historical data
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=date,
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow='TRADES',
        useRTH=True
    )
    
    # Convert to DataFrame
    df = util.df(bars)
    return df

# Alias for backward compatibility
get_price_data_for_given_stock = get_historical_price_data

def get_portfolio_holdings(ib=None, print_output=False):
    """
    Retrieves, formats, and optionally prints portfolio holdings from Interactive Brokers.
    
    Args:
        ib: An existing IB connection. If None, will create a new connection.
        print_output: Whether to print the formatted portfolio data
        
    Returns:
        A tuple containing (positions list, formatted string)
    """
    # Connect to IB if no connection was provided
    if ib is None or not ib.isConnected():
        ib = connect_to_ib()
        if ib is None:
            print("⛔ Failed to establish connection to IB")
            return None, None
        connect_needed = True
    else:
        connect_needed = False
    
    # Get portfolio data
    try:
        portfolio = ib.portfolio()
        print(f"📊 Retrieved {len(portfolio)} portfolio positions")
        
        # Get account values including cash balances
        account_values = ib.accountValues()
        
        # Extract cash balances and other account metrics
        cash_balances = {}
        account_metrics = {}
        base_currency = "USD"  # Default currency
        
        # These are the tags we want to extract for cash and account information
        cash_tags = ['TotalCashBalance', 'AvailableFunds', 'BuyingPower', 'ExcessLiquidity']
        metric_tags = ['NetLiquidation', 'GrossPositionValue', 'EquityWithLoanValue']
        
        for value in account_values:
            # Identify the base currency if available
            if value.tag == 'Currency' and value.value and value.currency == '':
                base_currency = value.value
                
            # Extract cash balances for the base currency
            if value.tag in cash_tags and value.currency == base_currency:
                cash_balances[value.tag] = float(value.value) if value.value else 0.0
            
            # Extract account metrics for the base currency
            if value.tag in metric_tags and value.currency == base_currency:
                account_metrics[value.tag] = float(value.value) if value.value else 0.0
        
        print(f"💰 Retrieved cash balances in {base_currency}")
        
        # Format the data for easier use
        positions = []
        for item in portfolio:
            position = {
                'contract': item.contract,
                'position': item.position,
                'marketPrice': item.marketPrice,
                'marketValue': item.marketValue,
                'averageCost': item.averageCost,
                'unrealizedPNL': item.unrealizedPNL,
                'realizedPNL': item.realizedPNL,
                'account': item.account
            }
            positions.append(position)
        
        # Format the portfolio data
        formatted_output = ""
        if positions and len(positions) > 0:
            # Calculate column widths based on content
            symbol_width = max(8, max(len(p['contract'].symbol) for p in positions))
            account_width = max(9, max(len(p['account']) for p in positions))
            
            # Create header for positions
            header = (
                f"{'Symbol':<{symbol_width}} | {'Position':>10} | {'Avg Cost':>10} | "
                f"{'Market Value':>14} | {'Price':>10} | {'Unrealized PNL':>15} | "
                f"{'Account':<{account_width}}"
            )
            separator = "-" * len(header)
            
            # Create formatted table for positions
            result = ["\n📊 PORTFOLIO POSITIONS", separator, header, separator]
            
            total_market_value = 0
            total_unrealized_pnl = 0
            
            # Add each position
            for p in positions:
                symbol = p['contract'].symbol
                position = p['position']
                price = p['marketPrice']
                market_value = p['marketValue']
                avg_cost = p['averageCost']
                unrealized_pnl = p['unrealizedPNL']
                account = p['account']
                
                total_market_value += market_value
                total_unrealized_pnl += unrealized_pnl
                
                result.append(
                    f"{symbol:<{symbol_width}} | {position:>10,.2f} | {avg_cost:>10,.2f} | "
                    f"{market_value:>14,.2f} | {price:>10,.2f} | {unrealized_pnl:>15,.2f} | "
                    f"{account:<{account_width}}"
                )
            
            # Add total row for positions
            result.append(separator)
            result.append(
                f"{'TOTAL':<{symbol_width}} | {' ':>10} | {' ':>10} | "
                f"{total_market_value:>14,.2f} | {' ':>10} | {total_unrealized_pnl:>15,.2f} | "
                f"{' ':<{account_width}}"
            )
            
            # Create a simpler table for cash balances with appropriate columns
            result.append("\n\n💰 CASH BALANCES")
            
            # Define columns for cash/metrics tables
            desc_width = 25
            value_width = 20
            curr_width = 5
            
            # Create header for cash table
            cash_header = f"{'Description':<{desc_width}} | {'Value':>{value_width}} | {'Currency':<{curr_width}}"
            cash_separator = "-" * len(cash_header)
            
            result.append(cash_separator)
            
            # Add cash rows with better formatting
            for tag, amount in cash_balances.items():
                # Format the tag name to be more readable
                formatted_tag = ' '.join(re.findall('[A-Z][a-z]*', tag))
                result.append(f"{formatted_tag:<{desc_width}} | {amount:>{value_width},.2f} | {base_currency:<{curr_width}}")
            
            # Create a similar table for account metrics
            result.append("\n\n📊 ACCOUNT METRICS")
            result.append(cash_separator)
            
            # Add account metric rows with consistent formatting
            for tag, amount in account_metrics.items():
                # Format the tag name to be more readable
                formatted_tag = ' '.join(re.findall('[A-Z][a-z]*', tag))
                result.append(f"{formatted_tag:<{desc_width}} | {amount:>{value_width},.2f} | {base_currency:<{curr_width}}")
            
            # Calculate portfolio allocation stats
            if 'NetLiquidation' in account_metrics and account_metrics['NetLiquidation'] > 0:
                # Calculate cash percentage
                cash_percent = cash_balances.get('TotalCashBalance', 0) / account_metrics['NetLiquidation'] * 100
                # Calculate equity percentage
                equity_percent = total_market_value / account_metrics['NetLiquidation'] * 100
                
                # Create allocation summary with percentages in dedicated column
                result.append("\n\n📈 ALLOCATION SUMMARY")
                
                # Create header for allocation table - add percentage column
                alloc_header = f"{'Description':<{desc_width}} | {'Value':>{value_width}} | {'Percentage':>12}"
                alloc_separator = "-" * len(alloc_header)
                
                result.append(alloc_separator)
                result.append(f"{'Cash Allocation':<{desc_width}} | {cash_balances.get('TotalCashBalance', 0):>{value_width},.2f} | {cash_percent:>11.2f}%")
                result.append(f"{'Equity Allocation':<{desc_width}} | {total_market_value:>{value_width},.2f} | {equity_percent:>11.2f}%")
                result.append(f"{'Total':<{desc_width}} | {account_metrics.get('NetLiquidation', 0):>{value_width},.2f} | {100:>11.2f}%")
            
            formatted_output = "\n".join(result)
        
        else:
            formatted_output = "No positions found."
            
        # Print output if requested
        if print_output:
            print("\n" + formatted_output)
                    
        return positions, formatted_output
        
    except Exception as e:
        print(f"⛔ Error retrieving portfolio: {e}")
        return None, None
    finally:
        # Disconnect only if we created the connection in this function
        if connect_needed and ib is not None and ib.isConnected():
            ib.disconnect()
            print("🔌 Disconnected from IB")

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

def calculate_beta(portfolio_returns, market_returns):
    """
    Calculate the beta (market risk) of a portfolio or stock
    
    Args:
        portfolio_returns: pandas Series or numpy array of portfolio/stock returns
        market_returns: pandas Series or numpy array of market returns (e.g. S&P 500)
        
    Returns:
        Beta value
    """
    # Convert inputs to pandas Series if they aren't already
    if not isinstance(portfolio_returns, pd.Series):
        portfolio_returns = pd.Series(portfolio_returns)
    if not isinstance(market_returns, pd.Series):
        market_returns = pd.Series(market_returns)
    
    # Ensure both series have the same index if they are pandas Series
    if hasattr(portfolio_returns, 'index') and hasattr(market_returns, 'index'):
        # Find common dates
        common_index = portfolio_returns.index.intersection(market_returns.index)
        
        if len(common_index) == 0:
            print("Warning: No overlapping dates between portfolio and market returns")
            return 0.0
            
        # Filter to common dates
        portfolio_returns = portfolio_returns.loc[common_index]
        market_returns = market_returns.loc[common_index]
    
    # If they're numpy arrays, ensure they have the same length
    elif len(portfolio_returns) != len(market_returns):
        # Use the shorter length
        min_length = min(len(portfolio_returns), len(market_returns))
        portfolio_returns = portfolio_returns[:min_length]
        market_returns = market_returns[:min_length]
        print(f"Warning: Returns series have different lengths. Using first {min_length} elements.")
    
    # Calculate covariance between portfolio and market
    covariance = np.cov(portfolio_returns, market_returns)[0, 1]
    
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
        return float('inf')
    
    downside_deviation = np.sqrt(np.mean(downside_returns**2))
    
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

def get_portfolio_returns(ib, symbols, duration='1 Y', bar_size='1 day'):
    """
    Get historical returns for portfolio stocks
    
    Args:
        ib: IB connection
        symbols: list of stock symbols
        duration: time period for data (default: '1 Y')
        bar_size: bar size for data (default: '1 day')
        
    Returns:
        DataFrame with returns for all symbols
    """
    all_data = {}
    missing_data = []
    
    for symbol in symbols:
        try:
            # Get price data
            df = get_price_data_for_given_stock(ib, symbol, duration, bar_size)
            
            if df is not None and not df.empty:
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

def calculate_alpha(portfolio_returns, market_returns, risk_free_rate, beta=None):
    """
    Calculate Alpha - excess return of investment relative to a benchmark
    
    Args:
        portfolio_returns: pandas Series or numpy array of portfolio returns
        market_returns: pandas Series or numpy array of market returns
        risk_free_rate: risk-free rate (annualized)
        beta: pre-calculated beta (if None, will be calculated)
        
    Returns:
        Alpha value
    """
    # Make sure we're working with common dates or lengths
    if not isinstance(portfolio_returns, pd.Series):
        portfolio_returns = pd.Series(portfolio_returns)
    if not isinstance(market_returns, pd.Series):
        market_returns = pd.Series(market_returns)
    
    # Align dates if series have indexes
    if hasattr(portfolio_returns, 'index') and hasattr(market_returns, 'index'):
        common_index = portfolio_returns.index.intersection(market_returns.index)
        if len(common_index) > 0:
            portfolio_returns = portfolio_returns.loc[common_index]
            market_returns = market_returns.loc[common_index]
    
    # Calculate average returns
    avg_portfolio_return = np.mean(portfolio_returns) * 252  # Annualize
    avg_market_return = np.mean(market_returns) * 252  # Annualize
    
    # Get or calculate beta
    if beta is None:
        beta = calculate_beta(portfolio_returns, market_returns)
    
    # Daily risk-free rate (assuming risk_free_rate is annual)
    daily_rf = risk_free_rate / 252
    
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
    annualized_return = (1 + total_return) ** (1 / years) - 1
    
    return annualized_return

def calculate_portfolio_metrics(ib, symbols, printOutput=True):
    """
    Calculate key performance metrics for a portfolio of stocks
    
    Args:
        ib: IB connection
        symbols: List of stock symbols in the portfolio
        printOutput: Whether to print metrics to console (default: True)
        
    Returns:
        Dictionary containing calculated metrics
    """
    # Get portfolio positions for weights calculation
    positions, _ = get_portfolio_holdings(ib, print_output=False)
    
    # Define time period for analysis
    duration = '2 Y'
    bar_size = '1 day'
    
    # Get price data for all portfolio symbols
    price_data = {}
    for symbol in symbols:
        df = get_historical_price_data(ib, symbol, duration, bar_size)
        if df is not None and not df.empty:
            # Ensure proper date index
            if 'date' in df.columns:
                df.set_index('date', inplace=True)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            price_data[symbol] = df['close']
    
    # Get market index (SPY) data for benchmark
    market_df = get_historical_price_data(ib, 'SPY', duration, bar_size)
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
    if printOutput:
        # Print portfolio summary
        print("\n📊 PORTFOLIO METRICS\n")
        
        if weight_method == "equal":
            print("Using equal weights for portfolio returns calculation\n")
        else:
            print("Using position market value weights for portfolio returns calculation\n")
            
        # Print metrics in formatted table
        print(f"Total Return: {metrics['total_return']*100:.2f}%")
        print(f"Annualized Return: {metrics['annualized_return']*100:.2f}%")
        
        if market_returns is not None:
            print(f"Market Total Return (SPY): {metrics['market_total_return']*100:.2f}%")
            print(f"Market Annualized Return (SPY): {metrics['market_annualized_return']*100:.2f}%")
            print(f"Beta: {metrics['beta']:.2f}")
            print(f"Alpha: {metrics['alpha']*100:.2f}%")
            
        print(f"Volatility (annualized): {metrics['volatility']*100:.2f}%")
        print(f"Historical VaR (99%): {metrics['historical_var_pct']*100:.2f}% (${metrics['historical_var_amount']:.2f})")
        print(f"Parametric VaR (99%): {metrics['parametric_var_pct']*100:.2f}% (${metrics['parametric_var_amount']:.2f})")
        print(f"Maximum Drawdown: {metrics['max_drawdown']*100:.2f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        print(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    
    # Calculate individual stock metrics
    stock_metrics = {}
    for symbol in returns_df.columns:
        stock_returns = returns_df[symbol].dropna()
        if len(stock_returns) > 0:
            stock_metrics[symbol] = calculate_stock_metrics(
                stock_returns, market_returns, positions, symbol, 
                periods_per_year, sqrt_periods
            )
    
    metrics['stock_metrics'] = stock_metrics
    
    # Print individual stock metrics table if requested
    if printOutput and stock_metrics:
        print_stock_metrics_table(stock_metrics)
    
    return metrics

def calculate_stock_metrics(stock_returns, market_returns, positions, symbol, periods_per_year, sqrt_periods):
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

def print_stock_metrics_table(stock_metrics):
    """Helper function to print a formatted table of individual stock metrics"""
    print("\n📊 INDIVIDUAL STOCK METRICS\n")
    
    # Define metrics to display
    metrics_to_display = [
        ("Total Return", lambda s: f"{stock_metrics[s]['total_return']*100:.2f}%"),
        ("Annualized Return", lambda s: f"{stock_metrics[s]['annualized_return']*100:.2f}%"),
        ("Volatility", lambda s: f"{stock_metrics[s]['volatility']*100:.2f}%"),
        ("Beta", lambda s: f"{stock_metrics[s]['beta']:.2f}" if 'beta' in stock_metrics[s] else "N/A"),
        ("Alpha", lambda s: f"{stock_metrics[s]['alpha']*100:.2f}%" if 'alpha' in stock_metrics[s] else "N/A"),
        ("Historical VaR (99%)", lambda s: f"{stock_metrics[s]['var_pct']*100:.2f}%"),
        ("Maximum Drawdown", lambda s: f"{stock_metrics[s]['max_drawdown']*100:.2f}%"),
        ("Sharpe Ratio", lambda s: f"{stock_metrics[s]['sharpe_ratio']:.2f}"),
        ("Sortino Ratio", lambda s: f"{stock_metrics[s]['sortino_ratio']:.2f}")
    ]
    
    # Calculate column widths
    metric_width = max(len(m[0]) for m in metrics_to_display) + 2
    symbols = sorted(stock_metrics.keys())
    
    # Pre-compute all values to determine column widths
    all_values = {}
    for symbol in symbols:
        all_values[symbol] = []
        for _, metric_fn in metrics_to_display:
            try:
                all_values[symbol].append(metric_fn(symbol))
            except:
                all_values[symbol].append("N/A")
    
    # Calculate optimal column width for each symbol
    column_widths = {}
    for symbol in symbols:
        column_widths[symbol] = max(len(symbol), max(len(val) for val in all_values[symbol])) + 2
    
    # Print header
    header = "Metric".ljust(metric_width) + "| " + " | ".join(s.ljust(column_widths[s]) for s in symbols)
    print(header)
    print("-" * len(header))
    
    # Print each metric row
    for i, (metric_name, _) in enumerate(metrics_to_display):
        row = metric_name.ljust(metric_width) + "| "
        values = []
        for symbol in symbols:
            try:
                val = all_values[symbol][i]
                values.append(val.ljust(column_widths[symbol]))
            except:
                values.append("N/A".ljust(column_widths[symbol]))
        print(row + " | ".join(values))

def calculate_monthly_portfolio_metrics(ib, symbols=None, market_symbol='SPY', duration='2 Y', confidence_level=0.99, risk_free_rate=0.03, use_position_weights=True, print_output=True):
    """
    Calculate portfolio metrics on a monthly basis
    
    Args:
        ib: IB connection
        symbols: list of stock symbols (if None, will use current portfolio holdings)
        market_symbol: market index symbol (default: 'SPY')
        duration: time period for data (default: '2 Y')
        confidence_level: confidence level for VaR (default: 0.99)
        risk_free_rate: risk-free rate (default: 0.03)
        use_position_weights: whether to use position weights (default: True)
        print_output: whether to print results (default: True)
        
    Returns:
        Dictionary containing monthly metrics
    """
    # Get symbols and positions from portfolio if not provided
    positions = None
    if symbols is None:
        positions, _ = get_portfolio_holdings(ib)
        if positions:
            symbols = [p['contract'].symbol for p in positions]
        else:
            if print_output:
                print("⚠️ No positions found in portfolio")
            return None
    
    # Get daily price data for all symbols for the specified duration
    if print_output:
        print(f"\n📈 MONTHLY PORTFOLIO PERFORMANCE ANALYSIS\n")
        print(f"🔍 Fetching daily price data for {len(symbols)} symbols over {duration}...")
    
    all_prices = {}
    for symbol in symbols:
        try:
            df = get_price_data_for_given_stock(ib, symbol, duration, '1 day')
            if df is not None and not df.empty:
                # Ensure the date is the index and properly formatted
                if 'date' in df.columns:
                    df.set_index('date', inplace=True)
                all_prices[symbol] = df['close']
                if print_output:
                    print(f"✅ Got {len(df)} data points for {symbol}")
        except Exception as e:
            if print_output:
                print(f"❌ Error getting data for {symbol}: {e}")
    
    # Get market price data
    market_df = get_price_data_for_given_stock(ib, market_symbol, duration, '1 day')
    if market_df is None or market_df.empty:
        if print_output:
            print(f"❌ Could not get market data for {market_symbol}")
        return None
    
    # Ensure the date is the index for market data too
    if 'date' in market_df.columns:
        market_df.set_index('date', inplace=True)
    
    market_prices = market_df['close']
    
    # Convert to DataFrame and handle missing data
    prices_df = pd.DataFrame(all_prices)
    if prices_df.empty:
        if print_output:
            print("❌ No price data available for any symbols")
        return None
    
    # Make sure index is datetime type
    if not isinstance(prices_df.index, pd.DatetimeIndex):
        try:
            prices_df.index = pd.to_datetime(prices_df.index)
        except Exception as e:
            if print_output:
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
            if print_output:
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
            if print_output:
                print(f"📊 Using actual position weights for portfolio returns calculation")
        else:
            weights = None
            if print_output:
                print(f"⚠️ Total portfolio value is zero or negative. Using equal weights.")
    
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
    overall_metrics = calculate_portfolio_metrics(ib, symbols, printOutput=False)
    
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
            if print_output:
                print(f"⚠️ Error processing month {year_month}: {e}")
            continue
    
    # Print monthly performance table
    if print_output and len(monthly_metrics) > 0:
        print("\n📊 MONTHLY PORTFOLIO PERFORMANCE BREAKDOWN\n")
        
        if not use_position_weights:
            print("Using equal weights for portfolio returns calculation")
            
        # Define columns and create format functions
        columns = [
            ("Month", lambda m, d: m),
            ("Return", lambda m, d: f"{d['total_return']*100:.2f}%"),
            ("vs SPY", lambda m, d: f"{d['relative_performance']*100:.2f}%"),
            ("Alpha", lambda m, d: f"{d['alpha']*100:.2f}%"),
            ("Beta", lambda m, d: f"{d['beta']:.2f}"),
            ("Vol", lambda m, d: f"{d['volatility']*100:.2f}%"),
            ("MaxDD", lambda m, d: f"{d['max_drawdown']*100:.2f}%"),
            ("Sharpe", lambda m, d: f"{d['sharpe_ratio']:.2f}"),
            ("Sortino", lambda m, d: f"{d['sortino_ratio']:.2f}")
        ]
        
        # Pre-compute all values to determine column widths
        all_values = {}
        for month, metrics in monthly_metrics.items():
            all_values[month] = []
            for _, format_fn in columns:
                try:
                    val = format_fn(month, metrics)
                    all_values[month].append(val)
                except:
                    all_values[month].append("N/A")
        
        # Calculate optimal column width for each column
        column_widths = {}
        for i, (col_name, _) in enumerate(columns):
            # Get the maximum width needed for this column across all months
            max_val_width = max(len(all_values[month][i]) for month in monthly_metrics.keys())
            column_widths[i] = max(len(col_name), max_val_width) + 2
        
        # Create header with proper column widths
        header = ""
        for i, (col_name, _) in enumerate(columns):
            header += col_name.ljust(column_widths[i]) + "| "
        header = header.rstrip("| ")
        
        print(header)
        print("-" * len(header))
        
        # Print each month's metrics row with proper alignment
        for month in sorted(monthly_metrics.keys()):
            row = ""
            for i, (_, format_fn) in enumerate(columns):
                try:
                    val = all_values[month][i]
                    row += val.ljust(column_widths[i]) + "| "
                except:
                    row += "N/A".ljust(column_widths[i]) + "| "
            print(row.rstrip("| "))
    
    # Calculate summary statistics
    positive_months = sum(1 for m in monthly_metrics.values() if m['total_return'] > 0)
    total_months = len(monthly_metrics)
    outperformance_months = sum(1 for m in monthly_metrics.values() if m['relative_performance'] > 0)
    
    if total_months > 0 and print_output:
        print("\n\n📊 MONTHLY SUMMARY STATISTICS\n")
        print(f"Total Months Analyzed: {total_months}")
        print(f"Positive Return Months: {positive_months} ({positive_months/total_months*100:.1f}%)")
        print(f"Months Outperforming SPY: {outperformance_months} ({outperformance_months/total_months*100:.1f}%)")
        
        # Find best and worst months
        if monthly_metrics:
            best_month = max(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
            worst_month = min(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
            
            print(f"\nBest Month: {best_month[0]} with {best_month[1]['total_return']*100:.2f}% return")
            print(f"Worst Month: {worst_month[0]} with {worst_month[1]['total_return']*100:.2f}% return")
    
    # Combine the results
    results = {
        'overall_metrics': overall_metrics,
        'monthly_metrics': monthly_metrics
    }
    
    return results

def calculate_monthly_stock_metrics(ib, symbol, market_symbol='SPY', 
                                  duration='2 Y', confidence_level=0.99, 
                                  risk_free_rate=0.03, printOutput=True):
    """
    Calculate monthly performance metrics for a single stock
    
    Args:
        ib: IB connection
        symbol: stock symbol to analyze
        market_symbol: symbol for market index (default: 'SPY')
        duration: time period for data (default: '2 Y')
        confidence_level: confidence level for VaR (default: 0.99)
        risk_free_rate: annualized risk-free rate (default: 0.03)
        printOutput: whether to print output (default: True)
        
    Returns:
        Dictionary containing overall metrics and monthly metrics
    """
    if printOutput:
        print(f"\n\n📈 APPLE (AAPL) STOCK ANALYSIS\n") if symbol == "AAPL" else print(f"\n\n📈 {symbol} STOCK ANALYSIS\n")
    
    # Get price data for the stock
    stock_df = get_price_data_for_given_stock(ib, symbol, duration, '1 day')
    if stock_df is None or stock_df.empty:
        if printOutput:
            print(f"Could not get price data for {symbol}")
        return None
    
    # Get market price data
    market_df = get_price_data_for_given_stock(ib, market_symbol, duration, '1 day')
    if market_df is None or market_df.empty:
        if printOutput:
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
        if printOutput:
            print(f"Insufficient data for {symbol} (found only {len(stock_returns)} data points)")
        return None
    
    # Calculate overall stock metrics first (this can be simplified but for consistency we'll use existing function)
    stock_metrics = {}
    
    # Create a fake portfolio with just this stock
    fake_positions = [{'contract': Stock(symbol, 'SMART', 'USD'), 'marketValue': 1}]
    fake_symbols = [symbol]
    overall_metrics = calculate_portfolio_metrics(ib, fake_symbols, printOutput=False)
    
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
    
    # Print individual stock monthly performance
    if printOutput and monthly_metrics:
        print(f"\n📊 MONTHLY PERFORMANCE FOR {symbol}\n")
        
        # Define columns and create format functions
        columns = [
            ("Month", lambda m, d: m),
            ("Return", lambda m, d: f"{d['total_return']*100:.2f}%"),
            ("vs SPY", lambda m, d: f"{d['relative_performance']*100:.2f}%"),
            ("Alpha", lambda m, d: f"{d['alpha']*100:.2f}%"),
            ("Beta", lambda m, d: f"{d['beta']:.2f}"),
            ("Volatility", lambda m, d: f"{d['volatility']*100:.2f}%"),
            ("MaxDD", lambda m, d: f"{d['max_drawdown']*100:.2f}%"),
            ("Sharpe", lambda m, d: f"{d['sharpe_ratio']:.2f}")
        ]
        
        # Pre-compute all values to determine column widths
        all_values = {}
        for month, metrics in monthly_metrics.items():
            all_values[month] = []
            for _, format_fn in columns:
                try:
                    val = format_fn(month, metrics)
                    all_values[month].append(val)
                except:
                    all_values[month].append("N/A")
        
        # Calculate optimal column width for each column
        column_widths = {}
        for i, (col_name, _) in enumerate(columns):
            # Get the maximum width needed for this column across all months
            max_val_width = max(len(all_values[month][i]) for month in monthly_metrics.keys())
            column_widths[i] = max(len(col_name), max_val_width) + 2
        
        # Create header with proper column widths
        header = ""
        for i, (col_name, _) in enumerate(columns):
            header += col_name.ljust(column_widths[i]) + "| "
        header = header.rstrip("| ")
        
        print(header)
        print("-" * len(header))
        
        # Print each month's metrics row with proper alignment
        for month in sorted(monthly_metrics.keys()):
            row = ""
            for i, (_, format_fn) in enumerate(columns):
                try:
                    val = all_values[month][i]
                    row += val.ljust(column_widths[i]) + "| "
                except:
                    row += "N/A".ljust(column_widths[i]) + "| "
            print(row.rstrip("| "))
    
    # Calculate summary statistics
    positive_months = sum(1 for m in monthly_metrics.values() if m['total_return'] > 0)
    total_months = len(monthly_metrics)
    outperformance_months = sum(1 for m in monthly_metrics.values() if m['relative_performance'] > 0)
    
    if total_months > 0 and printOutput:
        print("\n📊 MONTHLY SUMMARY STATISTICS\n")
        print(f"Total Months Analyzed: {total_months}")
        print(f"Positive Return Months: {positive_months} ({positive_months/total_months*100:.1f}%)")
        print(f"Months Outperforming SPY: {outperformance_months} ({outperformance_months/total_months*100:.1f}%)")
        
        # Find best and worst months
        best_month = max(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
        worst_month = min(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
        
        print(f"\nBest Month: {best_month[0]} with {best_month[1]['total_return']*100:.2f}% return")
        print(f"Worst Month: {worst_month[0]} with {worst_month[1]['total_return']*100:.2f}% return")
    
    # Print overall metrics for the stock if available
    if printOutput and overall_metrics and 'stock_metrics' in overall_metrics and symbol in overall_metrics['stock_metrics']:
        metrics = overall_metrics['stock_metrics'][symbol]
        
        print(f"\n📊 OVERALL METRICS FOR {symbol}\n")
        print(f"Total Return: {metrics['total_return']:.2%}")
        print(f"Annualized Return: {metrics['annualized_return']:.2%}")
        print(f"Volatility: {metrics['volatility']:.2%}")
        print(f"Beta: {metrics['beta']:.2f}")
        print(f"Alpha: {metrics['alpha']:.2%}")
        print(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        print(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    
    # Combine the results
    results = {
        'symbol': symbol,
        'overall_metrics': overall_metrics['stock_metrics'].get(symbol, {}) if overall_metrics and 'stock_metrics' in overall_metrics else {},
        'monthly_metrics': monthly_metrics
    }
    
    return results

def analyze_portfolio_diversification(ib=None, print_output=True):
    """
    Analyzes portfolio holdings to calculate exposure percentages by sector, industry, and sub-industry
    
    Args:
        ib: An existing IB connection. If None, will create a new connection.
        print_output: Whether to print the formatted analysis results
        
    Returns:
        Dictionary containing exposure data by sector, industry, and sub-industry
    """
    # Connect to IB if no connection was provided
    if ib is None or not ib.isConnected():
        ib = connect_to_ib()
        if ib is None:
            print("⛔ Failed to establish connection to IB")
            return None
        connect_needed = True
    else:
        connect_needed = False
    
    try:
        # Get portfolio holdings
        positions, _ = get_portfolio_holdings(ib, print_output=False)
        if not positions:
            print("⛔ No positions found in portfolio")
            return None
        
        # Extract symbols and create a symbol->market value mapping
        symbols = [p['contract'].symbol for p in positions]
        market_values = {p['contract'].symbol: p['marketValue'] for p in positions}
        total_portfolio_value = sum(market_values.values())
        
        if total_portfolio_value <= 0:
            print("⚠️ Portfolio total value is zero or negative")
            return None
        
        # Initialize dictionaries for classifications and exposures
        classifications = {}
        sector_exposure = {}
        industry_exposure = {}
        subcategory_exposure = {}
        
        # Get classifications for each symbol and calculate exposures
        for symbol in symbols:
            try:
                # Create and qualify contract
                contract = Stock(symbol, 'SMART', 'USD')
                qualified_contracts = ib.qualifyContracts(contract)
                
                if not qualified_contracts:
                    print(f"⚠️ Could not qualify contract for {symbol}")
                    continue
                
                contract = qualified_contracts[0]
                
                # Request contract details
                details = ib.reqContractDetails(contract)
                if not details:
                    print(f"⚠️ No details available for {symbol}")
                    continue
                
                # Extract classification data
                detail = details[0]
                
                # Get classifications - replace empty strings with placeholders
                sector = getattr(detail, 'industry', 'Unknown') or 'Unclassified'
                industry = getattr(detail, 'category', 'Unknown') or 'Unclassified' 
                subcategory = getattr(detail, 'subcategory', 'Unknown') or 'Unclassified'
                
                # Store classifications
                classifications[symbol] = {
                    'sector': sector,
                    'industry': industry,
                    'subcategory': subcategory
                }
                
                # Get market value and weight
                market_value = market_values.get(symbol, 0)
                weight = market_value / total_portfolio_value
                
                # Update sector exposure
                if sector not in sector_exposure:
                    sector_exposure[sector] = {
                        'value': 0,
                        'weight': 0,
                        'positions': []
                    }
                sector_exposure[sector]['value'] += market_value
                sector_exposure[sector]['weight'] += weight
                sector_exposure[sector]['positions'].append(symbol)
                
                # Update industry exposure
                if industry not in industry_exposure:
                    industry_exposure[industry] = {
                        'value': 0,
                        'weight': 0,
                        'positions': [],
                        'sector': sector
                    }
                industry_exposure[industry]['value'] += market_value
                industry_exposure[industry]['weight'] += weight
                industry_exposure[industry]['positions'].append(symbol)
                
                # Update subcategory exposure
                if subcategory not in subcategory_exposure:
                    subcategory_exposure[subcategory] = {
                        'value': 0,
                        'weight': 0,
                        'positions': [],
                        'industry': industry,
                        'sector': sector
                    }
                subcategory_exposure[subcategory]['value'] += market_value
                subcategory_exposure[subcategory]['weight'] += weight
                subcategory_exposure[subcategory]['positions'].append(symbol)
                
                print(f"✅ Processed {symbol}: {sector} / {industry} / {subcategory}")
                
                # Add a small delay to avoid overwhelming the API
                ib.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
        
        # Sort exposures by weight (descending)
        sorted_sector_exposure = dict(sorted(sector_exposure.items(), 
                                            key=lambda x: x[1]['weight'], 
                                            reverse=True))
        sorted_industry_exposure = dict(sorted(industry_exposure.items(), 
                                              key=lambda x: x[1]['weight'], 
                                              reverse=True))
        sorted_subcategory_exposure = dict(sorted(subcategory_exposure.items(), 
                                                 key=lambda x: x[1]['weight'], 
                                                 reverse=True))
        
        # Prepare result dictionary
        result = {
            'total_value': total_portfolio_value,
            'sector_exposure': sorted_sector_exposure,
            'industry_exposure': sorted_industry_exposure,
            'subcategory_exposure': sorted_subcategory_exposure,
            'classifications': classifications
        }
        
        # Print formatted output if requested
        if print_output:
            print("\n📊 PORTFOLIO DIVERSIFICATION ANALYSIS\n")
            print(f"Total Portfolio Value: ${total_portfolio_value:,.2f}")
            
            # Print sector exposure with improved formatting
            print("\n🔹 SECTOR EXPOSURE\n")
            # Define consistent column widths
            sector_col = 25
            weight_col = 10
            value_col = 15
            positions_col = 30
            
            # Create properly formatted header
            header = (
                f"{'Sector':<{sector_col}} | {'Weight':<{weight_col}} | {'Value':<{value_col}} | {'Positions':<{positions_col}}"
            )
            separator = "-" * len(header)
            
            print(header)
            print(separator)
            
            for sector, data in sorted_sector_exposure.items():
                # Replace empty sector name with placeholder
                sector_name = sector if sector else 'Unclassified'
                positions_str = ", ".join(data['positions'])
                weight_str = f"{data['weight']*100:.2f}%"
                value_str = f"${data['value']:,.2f}"
                print(f"{sector_name:<{sector_col}} | {weight_str:<{weight_col}} | {value_str:<{value_col}} | {positions_str:<{positions_col}}")
            
            # Print industry exposure with improved formatting
            print("\n🔹 INDUSTRY EXPOSURE\n")
            # Define consistent column widths
            industry_col = 25
            sector_col = 20
            weight_col = 10
            value_col = 15
            positions_col = 30
            
            # Create properly formatted header
            header = (
                f"{'Industry':<{industry_col}} | {'Sector':<{sector_col}} | {'Weight':<{weight_col}} | "
                f"{'Value':<{value_col}} | {'Positions':<{positions_col}}"
            )
            separator = "-" * len(header)
            
            print(header)
            print(separator)
            
            for industry, data in sorted_industry_exposure.items():
                # Replace empty industry or sector names with placeholders
                industry_name = industry if industry else 'Unclassified'
                sector_name = data['sector'] if data['sector'] else 'Unclassified'
                positions_str = ", ".join(data['positions'])
                weight_str = f"{data['weight']*100:.2f}%"
                value_str = f"${data['value']:,.2f}"
                print(
                    f"{industry_name:<{industry_col}} | {sector_name:<{sector_col}} | "
                    f"{weight_str:<{weight_col}} | {value_str:<{value_col}} | {positions_str:<{positions_col}}"
                )
            
            # Print subcategory exposure with improved formatting
            meaningful_subcategories = [sub for sub in sorted_subcategory_exposure.keys() 
                                           if sub not in ('Unknown', 'N/A', '')]
            
            if meaningful_subcategories:
                print("\n🔹 SUB-INDUSTRY EXPOSURE\n")
                
                # First, determine the maximum lengths for better column sizing
                max_subcategory = max(25, max(len(sub) for sub in subcategory_exposure.keys() if sub))
                max_industry = max(20, max(len(data['industry']) for data in subcategory_exposure.values() if data['industry']))
                
                # Fix column widths with padding
                subcategory_col = max_subcategory + 2  # Add some padding
                industry_col = max_industry + 2
                weight_col = 10
                value_col = 15
                
                # Create a properly formatted header
                header = (
                    f"{'Sub-Industry':<{subcategory_col}} | {'Industry':<{industry_col}} | {'Weight':<{weight_col}} | "
                    f"{'Value':<{value_col}} | {'Positions'}"
                )
                
                # Create separator with exact length
                separator = "-" * len(header)
                
                print(header)
                print(separator)
                
                for subcategory, data in sorted_subcategory_exposure.items():
                    # Skip truly empty categories
                    if subcategory in ('Unknown', 'N/A', '') and len(sorted_subcategory_exposure) > 1:
                        continue
                    
                    # Replace empty names with placeholders
                    subcategory_name = subcategory if subcategory else 'Unclassified'
                    industry_name = data['industry'] if data['industry'] else 'Unclassified'
                    
                    positions_str = ", ".join(data['positions'])
                    weight_str = f"{data['weight']*100:.2f}%"
                    value_str = f"${data['value']:,.2f}"
                    
                    # Match the exact header format
                    print(
                        f"{subcategory_name:<{subcategory_col}} | {industry_name:<{industry_col}} | "
                        f"{weight_str:<{weight_col}} | {value_str:<{value_col}} | {positions_str}"
                    )
            
            # Print stock classifications table
            print("\n🔹 INDIVIDUAL STOCK CLASSIFICATIONS\n")
            
            # Calculate column widths
            symbol_width = max(8, max(len(s) for s in symbols))
            sector_width = max(15, max(len(c['sector'] if c['sector'] else 'Unclassified') for c in classifications.values()))
            industry_width = max(15, max(len(c['industry'] if c['industry'] else 'Unclassified') for c in classifications.values()))
            subcategory_width = max(15, max(len(c['subcategory'] if c['subcategory'] else 'Unclassified') for c in classifications.values()))
            
            # Create header
            header = (
                f"{'Symbol':<{symbol_width}} | {'Sector':<{sector_width}} | "
                f"{'Industry':<{industry_width}} | {'Subcategory':<{subcategory_width}}"
            )
            separator = "-" * len(header)
            
            print(header)
            print(separator)
            
            # Print each stock's classification
            for symbol, data in classifications.items():
                sector_name = data['sector'] if data['sector'] else 'Unclassified'
                industry_name = data['industry'] if data['industry'] else 'Unclassified'
                subcategory_name = data['subcategory'] if data['subcategory'] else 'Unclassified'
                
                print(
                    f"{symbol:<{symbol_width}} | {sector_name:<{sector_width}} | "
                    f"{industry_name:<{industry_width}} | {subcategory_name:<{subcategory_width}}"
                )
        
        return result
    
    except Exception as e:
        print(f"❌ Error analyzing portfolio diversification: {e}")
        return None
    finally:
        # Disconnect only if we created the connection in this function
        if connect_needed and ib is not None and ib.isConnected():
            ib.disconnect()
            print("🔌 Disconnected from IB")

def analyze_portfolio_correlations(ib=None, symbols=None, duration='2 Y', bar_size='1 day', print_output=True, plot_heatmap=False):
    """
    Calculate correlation matrix for portfolio holdings
    
    Args:
        ib: An existing IB connection. If None, will create a new connection.
        symbols: List of stock symbols. If None, will get from portfolio.
        duration: Time period for data (default: '2 Y')
        bar_size: Bar size for data (default: '1 day')
        print_output: Whether to print the formatted correlation matrix
        plot_heatmap: Whether to plot a heatmap of correlations (requires matplotlib and seaborn)
        
    Returns:
        Pandas DataFrame containing the correlation matrix
    """
    # Connect to IB if no connection was provided
    if ib is None or not ib.isConnected():
        ib = connect_to_ib()
        if ib is None:
            if print_output:
                print("⛔ Failed to establish connection to IB")
            return None
        connect_needed = True
    else:
        connect_needed = False
    
    try:
        # Get symbols from portfolio if not provided
        if symbols is None:
            positions, _ = get_portfolio_holdings(ib, print_output=False)
            if positions:
                symbols = [p['contract'].symbol for p in positions]
                if print_output:
                    print(f"📊 Using {len(symbols)} symbols from portfolio")
            else:
                if print_output:
                    print("⛔ No positions found in portfolio and no symbols provided")
                return None
        
        # Get historical price data for all symbols
        if print_output:
            print(f"📈 Retrieving {duration} of {bar_size} price data for {len(symbols)} symbols...")
        price_data = {}
        
        for symbol in symbols:
            try:
                df = get_price_data_for_given_stock(ib, symbol, duration, bar_size)
                if df is not None and not df.empty:
                    # Ensure index is datetime
                    if not isinstance(df.index, pd.DatetimeIndex):
                        if 'date' in df.columns:
                            df.set_index('date', inplace=True)
                        df.index = pd.to_datetime(df.index)
                    
                    # Store close prices
                    price_data[symbol] = df['close']
                    if print_output:
                        print(f"✅ Got {len(df)} data points for {symbol}")
                else:
                    if print_output:
                        print(f"⚠️ No data available for {symbol}")
            except Exception as e:
                if print_output:
                    print(f"❌ Error retrieving data for {symbol}: {e}")
        
        if not price_data:
            if print_output:
                print("⛔ No price data retrieved for any symbols")
            return None
        
        # Convert to DataFrame
        all_prices = pd.DataFrame(price_data)
        
        # Calculate returns
        returns = all_prices.pct_change().dropna()
        
        # Calculate correlation matrix
        correlation_matrix = returns.corr()
        
        # Print formatted output if requested
        if print_output:
            print("\n📊 PORTFOLIO CORRELATION MATRIX\n")
            
            # Get the symbols for display
            symbols = correlation_matrix.index.tolist()
            
            # Calculate the optimal width for each column
            col_widths = {}
            for symbol in symbols:
                values = [f"{correlation_matrix.loc[symbol, col]:.2f}" for col in symbols]
                max_val_width = max(len(val) for val in values)
                col_widths[symbol] = max(len(symbol), max_val_width) + 2
                
            # Print the header row with symbol names
            header = " " * 8  # Space for row labels
            for symbol in symbols:
                header += symbol.ljust(col_widths[symbol]) + " "
            print(header)
            
            # Print each row of the correlation matrix
            for row_symbol in symbols:
                row = row_symbol.ljust(8)  # Left-align the row symbol
                for col_symbol in symbols:
                    value = correlation_matrix.loc[row_symbol, col_symbol]
                    row += f"{value:.2f}".ljust(col_widths[col_symbol]) + " "
                print(row)
        
        return correlation_matrix
        
    except Exception as e:
        if print_output:
            print(f"❌ Error analyzing portfolio correlations: {e}")
        return None
    finally:
        # Disconnect only if we created the connection in this function
        if connect_needed and ib is not None and ib.isConnected():
            ib.disconnect()
            if print_output:
                print("🔌 Disconnected from IB")

def generate_portfolio_report(capture_output=False, print_output=False):
    """
    Generate a comprehensive portfolio analysis report.
    
    Args:
        capture_output: Whether to capture and return the printed output as a string
        print_output: Whether to print the analysis results
        
    Returns:
        If capture_output is True: A string containing all printed output
        Otherwise: A tuple containing (positions, formatted_output, metrics, monthly_results, diversification, correlations)
    """
    # Set up output capture if requested
    output_buffer = None
    if capture_output:
        output_buffer = io.StringIO()
        redirect_context = redirect_stdout(output_buffer)
    else:
        redirect_context = nullcontext()  # No-op context manager
        
    with redirect_context:
        # Connect to Interactive Brokers
        ib = connect_to_ib()
        
        # Get portfolio holdings
        positions, formatted_output = get_portfolio_holdings(ib, print_output=print_output)
        
        # Initialize remaining variables
        metrics = None
        monthly_results = None
        correlations = None
        
        if positions:
            symbols = [p['contract'].symbol for p in positions]
            
            # Calculate portfolio metrics
            metrics = calculate_portfolio_metrics(ib, symbols, printOutput=print_output)
            
            # Calculate monthly portfolio metrics
            monthly_results = calculate_monthly_portfolio_metrics(ib, symbols, print_output=print_output)
            
            # Analyze portfolio correlations
            correlations = analyze_portfolio_correlations(ib, symbols, print_output=print_output)
        
        # Run stock analysis for AAPL
        aapl_results = calculate_monthly_stock_metrics(ib, "AAPL", printOutput=print_output)
        
        # Analyze portfolio diversification
        diversification = analyze_portfolio_diversification(ib, print_output=print_output)
    
    # Return the appropriate result based on mode
    if capture_output:
        captured_text = output_buffer.getvalue()
        if print_output:
            print(captured_text)
        return captured_text
    else:
        return positions, formatted_output, metrics, monthly_results, diversification, correlations


