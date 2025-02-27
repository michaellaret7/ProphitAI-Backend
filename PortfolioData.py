from ib_insync import IB, Stock, util, ContFuture
from datetime import datetime
from ib_insync import *
import numpy as np
import pandas as pd
from scipy import stats
import re

def connect_to_ib():
    ib = IB()
    if ib.isConnected():
        ib.disconnect()

    connected = False

    for port in [4002, 7497]:
        for clientId in range(7):  # Try client IDs from 0 to 6
            try:
                ib.connect('127.0.0.1', port, clientId=clientId)
                connected = True
                print(f"🌐 Connected successfully on port {port} with clientId {clientId}")
                break  # Break out of the clientId loop
            except Exception as e:
                print(f"🚨 Failed to connect on port {port} with clientId {clientId}: {e}")
                pass
        
        if connected:
            break  # Break out of the port loop if we're connected
    
    if not connected:
        print("⛔ Could not connect to IB on any port with any clientId")
        return None

    return ib

def get_price_data_for_given_stock(ib, symbol, duration='1 D', barSize='1 min', date=None):
    contract = Stock(symbol, 'SMART', 'USD')
    ticker = ib.qualifyContracts(contract)[0]

    if date is not None and '-' in date:
        date = date.replace('-', '')

    if date is not None:
        date = date + ' 16:00:00'
    else:
        date = ''

    bars = ib.reqHistoricalData(
        contract,
        endDateTime=date,
        durationStr=duration,
        barSizeSetting=barSize,
        whatToShow='TRADES',
        useRTH=True
    )
    df = util.df(bars)

    return df

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
                f"{'Symbol':<{symbol_width}} | {'Position':>10} | {'Price':>10} | "
                f"{'Market Value':>14} | {'Avg Cost':>10} | {'Unrealized PNL':>15} | "
                f"{'Account':<{account_width}}"
            )
            separator = "-" * len(header)
            
            # Create formatted table for positions
            result = ["\n📊 PORTFOLIO POSITIONS", separator]
            
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
                    f"{symbol:<{symbol_width}} | {position:>10,.2f} | {price:>10,.2f} | "
                    f"{market_value:>14,.2f} | {avg_cost:>10,.2f} | {unrealized_pnl:>15,.2f} | "
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
        if len(returns) < trading_days:
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

def calculate_portfolio_metrics(ib, symbols=None, market_symbol='SPY', duration='1 Y', bar_size='1 day', confidence_level=0.99, risk_free_rate=0.03,use_position_weights=True):
    """
    Calculate all risk metrics for a portfolio
    
    Args:
        ib: IB connection
        symbols: list of stock symbols (if None, will get from portfolio)
        market_symbol: symbol for market index (default: 'SPY')
        duration: time period for data (default: '1 Y')
        bar_size: bar size for data (default: '1 day')
        confidence_level: confidence level for VaR (default: 0.99 or 99%)
        risk_free_rate: annualized risk-free rate (default: 0.03 or 3%)
        use_position_weights: whether to use actual position weights (default: True)
        
    Returns:
        Dictionary of portfolio metrics
    """
    # Get symbols and positions from portfolio if not provided
    positions = None
    if symbols is None:
        positions, _ = get_portfolio_holdings(ib)
        if positions:
            symbols = [p['contract'].symbol for p in positions]
        else:
            print("No positions found in portfolio")
            return None
    
    # Get position weights if needed
    weights = None
    if use_position_weights and positions:
        # Create weights dictionary based on market value
        weights = {p['contract'].symbol: p['marketValue'] for p in positions}
        total_value = sum(weights.values())
        
        if total_value > 0:
            weights = {k: v / total_value for k, v in weights.items()}
            print(f"Using actual position weights for portfolio returns calculation")
        else:
            weights = None
            print(f"Warning: Total portfolio value is zero or negative. Using equal weights.")
    
    # Get returns for all symbols
    returns_df = get_portfolio_returns(ib, symbols, duration, bar_size)
    if returns_df is None or returns_df.empty:
        print("Could not get returns data for portfolio")
        return None
    
    # Get market returns
    market_df = get_price_data_for_given_stock(ib, market_symbol, duration, bar_size)
    if market_df is None or market_df.empty:
        print(f"Could not get market data for {market_symbol}")
        return None
    
    market_returns = market_df['close'].pct_change().dropna()
    
    # Calculate portfolio returns using weights if available
    if weights is not None:
        # Filter weights to only include symbols with data
        available_symbols = set(returns_df.columns)
        filtered_weights = {k: v for k, v in weights.items() if k in available_symbols}
        
        # Re-normalize weights if some symbols were filtered out
        total = sum(filtered_weights.values())
        if total > 0:
            filtered_weights = {k: v / total for k, v in filtered_weights.items()}
            
            # Calculate weighted returns
            weighted_returns = pd.DataFrame()
            for symbol, weight in filtered_weights.items():
                weighted_returns[symbol] = returns_df[symbol] * weight
            
            portfolio_returns = weighted_returns.sum(axis=1)
            print(f"Calculated weighted portfolio returns using {len(filtered_weights)} positions")
        else:
            # Fall back to equal weights if filtering removed all weights
            portfolio_returns = returns_df.mean(axis=1)
            print(f"Warning: No valid weights after filtering. Using equal weights.")
    else:
        # Use equal-weighted returns
        portfolio_returns = returns_df.mean(axis=1)
        print(f"Using equal weights for portfolio returns calculation")
    
    # Get cumulative returns for drawdown calculation
    cumulative_returns = (1 + portfolio_returns).cumprod()
    
    # Get annualization factors based on bar_size
    periods_per_year, sqrt_periods = get_annualization_factor(bar_size)
    
    # Calculate total and annualized returns for portfolio
    total_return = calculate_total_return(portfolio_returns)
    annualized_return = calculate_annualized_return(portfolio_returns, periods_per_year)
    
    # Calculate market returns for comparison
    market_total_return = calculate_total_return(market_returns)
    market_annualized_return = calculate_annualized_return(market_returns, periods_per_year)
    
    # Calculate portfolio value if positions exist
    portfolio_value = sum(p['marketValue'] for p in positions) if positions else 1
    
    # Calculate metrics
    beta = calculate_beta(portfolio_returns, market_returns)
    max_drawdown = calculate_max_drawdown(cumulative_returns)
    var_pct, var_amount = calculate_var(portfolio_returns, confidence_level, portfolio_value)
    param_var_pct, param_var_amount = calculate_parametric_var(portfolio_returns, confidence_level, portfolio_value)
    
    volatility = calculate_volatility(portfolio_returns, True, periods_per_year)
    sharpe_ratio = calculate_sharpe_ratio(portfolio_returns, risk_free_rate, True, periods_per_year)
    calmar_ratio = calculate_calmar_ratio(portfolio_returns, max_drawdown, periods_per_year)
    
    metrics = {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'market_total_return': market_total_return,
        'market_annualized_return': market_annualized_return,
        'volatility': volatility,
        'beta': beta,
        'alpha': calculate_alpha(portfolio_returns, market_returns, risk_free_rate, beta),
        'historical_var_pct': var_pct,
        'historical_var_amount': var_amount,
        'parametric_var_pct': param_var_pct,
        'parametric_var_amount': param_var_amount,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'calmar_ratio': calmar_ratio
    }
    
    # Calculate individual stock metrics
    stock_metrics = {}
    for symbol in returns_df.columns:
        stock_returns = returns_df[symbol].dropna()
        if len(stock_returns) > 0:
            stock_cum_returns = (1 + stock_returns).cumprod()
            stock_beta = calculate_beta(stock_returns, market_returns)
            stock_max_drawdown = calculate_max_drawdown(stock_cum_returns)
            
            # Get stock value if positions exist
            stock_value = next((p['marketValue'] for p in positions if p['contract'].symbol == symbol), 1) if positions else 1
            
            stock_var_pct, stock_var_amount = calculate_var(stock_returns, confidence_level, stock_value)
            stock_param_var_pct, stock_param_var_amount = calculate_parametric_var(stock_returns, confidence_level, stock_value)
            
            stock_metrics[symbol] = {
                'total_return': calculate_total_return(stock_returns),
                'annualized_return': calculate_annualized_return(stock_returns, periods_per_year),
                'volatility': calculate_volatility(stock_returns, True, periods_per_year),
                'beta': stock_beta,
                'alpha': calculate_alpha(stock_returns, market_returns, risk_free_rate, stock_beta),
                'historical_var_pct': stock_var_pct,
                'historical_var_amount': stock_var_amount,
                'parametric_var_pct': stock_param_var_pct,
                'parametric_var_amount': stock_param_var_amount,
                'max_drawdown': stock_max_drawdown,
                'sharpe_ratio': calculate_sharpe_ratio(stock_returns, risk_free_rate, True, periods_per_year),
                'calmar_ratio': calculate_calmar_ratio(stock_returns, stock_max_drawdown, periods_per_year)
            }
    
    metrics['stock_metrics'] = stock_metrics
    
    return metrics

def calculate_monthly_portfolio_metrics(ib, symbols=None, market_symbol='SPY', duration='2 Y', confidence_level=0.99, risk_free_rate=0.03, use_position_weights=True, print_output=False):
    """
    Calculate portfolio metrics on a month-by-month basis
    
    Args:
        ib: IB connection
        symbols: list of stock symbols (if None, will get from portfolio)
        market_symbol: symbol for market index (default: 'SPY')
        duration: time period for data (default: '2 Y')
        confidence_level: confidence level for VaR (default: 0.99)
        risk_free_rate: annualized risk-free rate (default: 0.03)
        use_position_weights: whether to use actual position weights (default: True)
        print_output: whether to print monthly performance table (default: False)
        
    Returns:
        Dictionary containing overall metrics and monthly metrics
    """
    # Get symbols and positions from portfolio if not provided
    positions = None
    if symbols is None:
        positions, _ = get_portfolio_holdings(ib)
        if positions:
            symbols = [p['contract'].symbol for p in positions]
        else:
            print("No positions found in portfolio")
            return None
    
    # Get daily price data for all symbols for the specified duration
    print(f"Fetching daily price data for {len(symbols)} symbols over {duration}...")
    all_prices = {}
    for symbol in symbols:
        try:
            df = get_price_data_for_given_stock(ib, symbol, duration, '1 day')
            if df is not None and not df.empty:
                # Ensure the date is the index and properly formatted
                if 'date' in df.columns:
                    df.set_index('date', inplace=True)
                all_prices[symbol] = df['close']
        except Exception as e:
            print(f"Error getting data for {symbol}: {e}")
    
    # Get market price data
    market_df = get_price_data_for_given_stock(ib, market_symbol, duration, '1 day')
    if market_df is None or market_df.empty:
        print(f"Could not get market data for {market_symbol}")
        return None
    
    # Ensure the date is the index for market data too
    if 'date' in market_df.columns:
        market_df.set_index('date', inplace=True)
    
    market_prices = market_df['close']
    
    # Convert to DataFrame and handle missing data
    prices_df = pd.DataFrame(all_prices)
    if prices_df.empty:
        print("No price data available for any symbols")
        return None
    
    # Make sure index is datetime type
    if not isinstance(prices_df.index, pd.DatetimeIndex):
        try:
            prices_df.index = pd.to_datetime(prices_df.index)
        except Exception as e:
            print(f"Error converting index to datetime: {e}")
            return None
    
    # Calculate daily returns
    returns_df = prices_df.pct_change(fill_method=None).dropna(how='all')
    market_returns = market_prices.pct_change(fill_method=None).dropna()
    
    # Get position weights if available
    weights = None
    if use_position_weights and positions:
        # Create weights dictionary based on market value
        weights = {p['contract'].symbol: p['marketValue'] for p in positions}
        total_value = sum(weights.values())
        
        if total_value > 0:
            weights = {k: v / total_value for k, v in weights.items()}
            print(f"Using actual position weights for portfolio returns calculation")
        else:
            weights = None
            print(f"Warning: Total portfolio value is zero or negative. Using equal weights.")
    
    # Calculate portfolio returns
    if weights is not None:
        # Filter weights to only include symbols with data
        available_symbols = set(returns_df.columns)
        filtered_weights = {k: v for k, v in weights.items() if k in available_symbols}
        
        # Re-normalize weights if some symbols were filtered out
        total = sum(filtered_weights.values())
        if total > 0:
            filtered_weights = {k: v / total for k, v in filtered_weights.items()}
            
            # Calculate weighted returns for each day
            portfolio_returns = pd.Series(0, index=returns_df.index)
            for symbol, weight in filtered_weights.items():
                portfolio_returns += returns_df[symbol].fillna(0) * weight
            
            print(f"Calculated weighted portfolio returns using {len(filtered_weights)} positions")
        else:
            # Fall back to equal weights if filtering removed all weights
            portfolio_returns = returns_df.mean(axis=1)
            print(f"Warning: No valid weights after filtering. Using equal weights.")
    else:
        # Use equal-weighted returns
        portfolio_returns = returns_df.mean(axis=1)
        print(f"Using equal weights for portfolio returns calculation")
    
    # Group by year and month
    # Ensure we're working with a DatetimeIndex
    portfolio_returns.index = pd.to_datetime(portfolio_returns.index)
    portfolio_returns = portfolio_returns.sort_index()
    market_returns.index = pd.to_datetime(market_returns.index)
    market_returns = market_returns.sort_index()
    
    # Create year-month columns for grouping
    portfolio_returns_monthly = pd.DataFrame(portfolio_returns)
    portfolio_returns_monthly.columns = ['returns']  # Rename for clarity
    portfolio_returns_monthly['year'] = portfolio_returns_monthly.index.year
    portfolio_returns_monthly['month'] = portfolio_returns_monthly.index.month
    portfolio_returns_monthly['year_month'] = portfolio_returns_monthly.index.strftime('%Y-%m')
    
    market_returns_monthly = pd.DataFrame(market_returns)
    market_returns_monthly.columns = ['returns']  # Rename for clarity
    market_returns_monthly['year'] = market_returns_monthly.index.year
    market_returns_monthly['month'] = market_returns_monthly.index.month
    market_returns_monthly['year_month'] = market_returns_monthly.index.strftime('%Y-%m')
    
    # Calculate overall portfolio metrics first
    overall_metrics = calculate_portfolio_metrics(ib, symbols, market_symbol, duration, '1 day', 
                                               confidence_level, risk_free_rate, use_position_weights)
    
    # Initialize dictionary for monthly metrics
    monthly_metrics = {}
    
    # Group returns by year-month
    grouped_returns = portfolio_returns_monthly.groupby('year_month')
    grouped_market = market_returns_monthly.groupby('year_month')
    
    # Get the unique year-months
    year_months = sorted(portfolio_returns_monthly['year_month'].unique())
    
    # Process each month (without debug prints)
    for year_month in year_months:
        try:
            # Get returns for this month
            month_portfolio = grouped_returns.get_group(year_month)['returns']
            
            # Try to get market returns for this month
            try:
                month_market = grouped_market.get_group(year_month)['returns']
            except KeyError:
                # Find overlapping dates
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
                'trading_days': len(month_portfolio)
            }
            
        except KeyError:
            continue
    
    # Format the monthly metrics for display only if requested
    if print_output:
        print("\n📊 MONTHLY PORTFOLIO PERFORMANCE\n")
        
        # Create header
        headers = ["Month", "Return", "vs SPY", "Alpha", "Beta", "Volatility", "MaxDD", "Sharpe", "VaR(99%)"]
        header_format = "{:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}"
        print(header_format.format(*headers))
        print("-" * 100)
        
        # Print each month's metrics
        for year_month in sorted(monthly_metrics.keys()):
            m = monthly_metrics[year_month]
            print(header_format.format(
                year_month,
                f"{m['total_return']:.2%}",
                f"{m['relative_performance']:.2%}",
                f"{m['alpha']:.2%}",
                f"{m['beta']:.2f}",
                f"{m['volatility']:.2%}",
                f"{m['max_drawdown']:.2%}",
                f"{m['sharpe_ratio']:.2f}",
                f"{m['historical_var_pct']:.2%}"
            ))
    
    # Combine the results
    results = {
        'overall_metrics': overall_metrics,
        'monthly_metrics': monthly_metrics
    }
    
    return results

def calculate_monthly_stock_metrics(ib, symbol, market_symbol='SPY', 
                                  duration='2 Y', confidence_level=0.99, 
                                  risk_free_rate=0.03):
    """
    Calculate monthly performance metrics for a single stock
    
    Args:
        ib: IB connection
        symbol: stock symbol to analyze
        market_symbol: symbol for market index (default: 'SPY')
        duration: time period for data (default: '2 Y')
        confidence_level: confidence level for VaR (default: 0.99)
        risk_free_rate: annualized risk-free rate (default: 0.03)
        
    Returns:
        Dictionary containing overall metrics and monthly metrics
    """
    print(f"📈 Analyzing monthly performance for {symbol} over {duration}...")
    
    # Get price data for the stock
    stock_df = get_price_data_for_given_stock(ib, symbol, duration, '1 day')
    if stock_df is None or stock_df.empty:
        print(f"Could not get price data for {symbol}")
        return None
    
    # Get market price data
    market_df = get_price_data_for_given_stock(ib, market_symbol, duration, '1 day')
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
    fake_positions = [{'contract': Stock(symbol, 'SMART', 'USD'), 'marketValue': 1}]
    fake_symbols = [symbol]
    overall_metrics = calculate_portfolio_metrics(ib, fake_symbols, market_symbol, duration, '1 day', 
                                                confidence_level, risk_free_rate, False)
    
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
                'trading_days': len(month_stock)
            }
            
        except KeyError:
            continue
    
    # Format and display the monthly metrics
    print(f"\n📊 MONTHLY PERFORMANCE FOR {symbol}\n")
    
    # Create header
    headers = ["Month", "Return", "vs SPY", "Alpha", "Beta", "Volatility", "MaxDD", "Sharpe", "VaR(99%)"]
    header_format = "{:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}"
    print(header_format.format(*headers))
    print("-" * 100)
    
    # Print each month's metrics
    for year_month in sorted(monthly_metrics.keys()):
        m = monthly_metrics[year_month]
        print(header_format.format(
            year_month,
            f"{m['total_return']:.2%}",
            f"{m['relative_performance']:.2%}",
            f"{m['alpha']:.2%}",
            f"{m['beta']:.2f}",
            f"{m['volatility']:.2%}",
            f"{m['max_drawdown']:.2%}",
            f"{m['sharpe_ratio']:.2f}",
            f"{m['historical_var_pct']:.2%}"
        ))
    
    # Calculate summary statistics
    positive_months = sum(1 for m in monthly_metrics.values() if m['total_return'] > 0)
    total_months = len(monthly_metrics)
    outperformance_months = sum(1 for m in monthly_metrics.values() if m['relative_performance'] > 0)
    
    if total_months > 0:
        print("\n📊 MONTHLY SUMMARY STATISTICS\n")
        print(f"Total Months Analyzed: {total_months}")
        print(f"Positive Return Months: {positive_months} ({positive_months/total_months:.1%})")
        print(f"Months Outperforming SPY: {outperformance_months} ({outperformance_months/total_months:.1%})")
        
        # Find best and worst months
        best_month = max(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
        worst_month = min(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
        
        print(f"\nBest Month: {best_month[0]} with {best_month[1]['total_return']:.2%} return")
        print(f"Worst Month: {worst_month[0]} with {worst_month[1]['total_return']:.2%} return")
    
    # Combine the results
    results = {
        'symbol': symbol,
        'overall_metrics': overall_metrics['stock_metrics'].get(symbol, {}),
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
                weight_str = f"{data['weight']:.2%}"
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
                weight_str = f"{data['weight']:.2%}"
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
                    weight_str = f"{data['weight']:.2%}"
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
                print(f"📊 Using {len(symbols)} symbols from portfolio")
            else:
                print("⛔ No positions found in portfolio and no symbols provided")
                return None
        
        # Get historical price data for all symbols
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
                    print(f"✅ Got {len(df)} data points for {symbol}")
                else:
                    print(f"⚠️ No data available for {symbol}")
            except Exception as e:
                print(f"❌ Error retrieving data for {symbol}: {e}")
        
        if not price_data:
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
            
            # Format the matrix for display - fix for applymap deprecation warning
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            pd.set_option('display.precision', 2)
            
            # Create formatted version of correlation matrix without using deprecated applymap
            formatted_corr = pd.DataFrame(
                [[f"{val:.2f}" for val in row] for row in correlation_matrix.values],
                index=correlation_matrix.index,
                columns=correlation_matrix.columns
            )
            
            print(formatted_corr)
        
        return correlation_matrix
        
    except Exception as e:
        print(f"❌ Error analyzing portfolio correlations: {e}")
        return None
    finally:
        # Disconnect only if we created the connection in this function
        if connect_needed and ib is not None and ib.isConnected():
            ib.disconnect()
            print("🔌 Disconnected from IB")

# Test code
if __name__ == "__main__":
    ib = connect_to_ib()
    
    # Get portfolio holdings and calculate metrics
    positions, formatted_output = get_portfolio_holdings(ib, print_output=True)
    
    if positions:
        symbols = [p['contract'].symbol for p in positions]
        print("\n📊 PORTFOLIO METRICS\n")
        metrics = calculate_portfolio_metrics(ib, symbols)
        
        if metrics:
            print(f"Total Return: {metrics['total_return']:.2%}")
            print(f"Annualized Return: {metrics['annualized_return']:.2%}")
            print(f"Market Total Return (SPY): {metrics['market_total_return']:.2%}")
            print(f"Market Annualized Return (SPY): {metrics['market_annualized_return']:.2%}")
            print(f"Volatility (annualized): {metrics['volatility']:.2%}")
            print(f"Beta: {metrics['beta']:.2f}")
            print(f"Alpha: {metrics['alpha']:.2%}")
            print(f"Historical VaR (99%): {metrics['historical_var_pct']:.2%} (${metrics['historical_var_amount']:.2f})")
            print(f"Parametric VaR (99%): {metrics['parametric_var_pct']:.2%} (${metrics['parametric_var_amount']:.2f})")
            print(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
            print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")
            
            print("\n📊 INDIVIDUAL STOCK METRICS\n")
            for symbol, stock_metric in metrics['stock_metrics'].items():
                print(f"{symbol}:")
                print(f"  Total Return: {stock_metric['total_return']:.2%}")
                print(f"  Annualized Return: {stock_metric['annualized_return']:.2%}")
                print(f"  Volatility: {stock_metric['volatility']:.2%}")
                print(f"  Beta: {stock_metric['beta']:.2f}")
                print(f"  Alpha: {stock_metric['alpha']:.2%}")
                print(f"  Historical VaR (99%): {stock_metric['historical_var_pct']:.2%} (${stock_metric['historical_var_amount']:.2f})")
                print(f"  Parametric VaR (99%): {stock_metric['parametric_var_pct']:.2%} (${stock_metric['parametric_var_amount']:.2f})")
                print(f"  Maximum Drawdown: {stock_metric['max_drawdown']:.2%}")
                print(f"  Sharpe Ratio: {stock_metric['sharpe_ratio']:.2f}")
                print(f"  Calmar Ratio: {stock_metric['calmar_ratio']:.2f}")
                print()
    
        print("\n📅 MONTHLY PORTFOLIO PERFORMANCE BREAKDOWN\n")
        
        # Calculate and get the monthly results - with print_output=False
        monthly_results = calculate_monthly_portfolio_metrics(ib, symbols, duration='2 Y', print_output=False)
        
        if monthly_results and 'monthly_metrics' in monthly_results:
            # Get the monthly metrics
            monthly_data = monthly_results['monthly_metrics']
            
            # Sort months chronologically
            sorted_months = sorted(monthly_data.keys())
            
            # Create detailed table with all metrics
            month_detail_format = "{:<10} | {:<8} | {:<8} | {:<8} | {:<8} | {:<8} | {:<8} | {:<8}"
            print(month_detail_format.format(
                "Month", "Return", "vs SPY", "Alpha", "Beta", "Vol", "MaxDD", "Sharpe"
            ))
            print("-" * 80)
            
            # Print each month's detailed metrics
            for month in sorted_months:
                m = monthly_data[month]
                print(month_detail_format.format(
                    month,
                    f"{m['total_return']:.2%}",
                    f"{m['relative_performance']:.2%}",
                    f"{m['alpha']:.2%}",
                    f"{m['beta']:.2f}",
                    f"{m['volatility']:.2%}",
                    f"{m['max_drawdown']:.2%}",
                    f"{m['sharpe_ratio']:.2f}"
                ))
            
            # Calculate and display summary statistics
            positive_months = sum(1 for m in monthly_data.values() if m['total_return'] > 0)
            total_months = len(monthly_data)
            outperformance_months = sum(1 for m in monthly_data.values() if m['relative_performance'] > 0)
            
            if total_months > 0:
                print("\n📊 MONTHLY SUMMARY STATISTICS\n")
                print(f"Total Months Analyzed: {total_months}")
                print(f"Positive Return Months: {positive_months} ({positive_months/total_months:.1%})")
                print(f"Months Outperforming SPY: {outperformance_months} ({outperformance_months/total_months:.1%})")
                
                # Find best and worst months
                best_month = max(monthly_data.items(), key=lambda x: x[1]['total_return'])
                worst_month = min(monthly_data.items(), key=lambda x: x[1]['total_return'])
                
                print(f"\nBest Month: {best_month[0]} with {best_month[1]['total_return']:.2%} return")
                print(f"Worst Month: {worst_month[0]} with {worst_month[1]['total_return']:.2%} return")
    
    # Run individual stock analysis for AAPL
    print("\n\n📈 APPLE (AAPL) STOCK ANALYSIS\n")
    aapl_results = calculate_monthly_stock_metrics(ib, "AAPL", duration='2 Y')
    
    # Overall metrics for AAPL
    if aapl_results and 'overall_metrics' in aapl_results and aapl_results['overall_metrics']:
        metrics = aapl_results['overall_metrics']
        
        print(f"\n📊 OVERALL METRICS FOR AAPL\n")
        print(f"Total Return: {metrics['total_return']:.2%}")
        print(f"Annualized Return: {metrics['annualized_return']:.2%}")
        print(f"Volatility: {metrics['volatility']:.2%}")
        print(f"Beta: {metrics['beta']:.2f}")
        print(f"Alpha: {metrics['alpha']:.2%}")
        print(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")

    # Analyze portfolio diversification
    print("\n📊 ANALYZING PORTFOLIO DIVERSIFICATION\n")
    diversification = analyze_portfolio_diversification(ib, print_output=True)

    # Analyze portfolio correlations
    print("\n📊 ANALYZING PORTFOLIO CORRELATIONS\n")
    correlation_matrix = analyze_portfolio_correlations(ib, duration='2 Y', bar_size='1 day')
    
    if ib and ib.isConnected():
        ib.disconnect()

