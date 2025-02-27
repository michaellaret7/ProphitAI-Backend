from ib_insync import IB, Stock, util, ContFuture
from datetime import datetime
from ib_insync import *
import numpy as np
import pandas as pd
from scipy import stats

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
            
            # Create header
            header = (
                f"{'Symbol':<{symbol_width}} | {'Position':>10} | {'Price':>10} | "
                f"{'Market Value':>14} | {'Avg Cost':>10} | {'Unrealized PNL':>15} | "
                f"{'Account':<{account_width}}"
            )
            separator = "-" * len(header)
            
            # Create formatted table
            result = [header, separator]
            
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
                
                row = (
                    f"{symbol:<{symbol_width}} | {position:>10,.0f} | {price:>10,.2f} | "
                    f"{market_value:>14,.2f} | {avg_cost:>10,.2f} | {unrealized_pnl:>15,.2f} | "
                    f"{account:<{account_width}}"
                )
                result.append(row)
            
            # Add summary row
            result.append(separator)
            summary = (
                f"{'TOTAL':<{symbol_width}} | {'':<10} | {'':<10} | "
                f"{total_market_value:>14,.2f} | {'':<10} | {total_unrealized_pnl:>15,.2f} | "
                f"{'':<{account_width}}"
            )
            result.append(summary)
            
            formatted_output = "\n".join(result)
        else:
            formatted_output = "No portfolio positions found."
        
        # Print the formatted output if requested
        if print_output:
            print("\n📊 PORTFOLIO HOLDINGS\n")
            print(formatted_output)
        
        return positions, formatted_output
        
    except Exception as e:
        print(f"❌ Error retrieving portfolio data: {e}")
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
    # Calculate average returns
    avg_portfolio_return = np.mean(portfolio_returns) * 252  # Annualize
    avg_market_return = np.mean(market_returns) * 252  # Annualize
    
    # Get or calculate beta
    if beta is None:
        beta = calculate_beta(portfolio_returns, market_returns)
    
    # Calculate alpha using CAPM
    alpha = avg_portfolio_return - (risk_free_rate + beta * (avg_market_return - risk_free_rate))
    
    return alpha

def calculate_calmar_ratio(returns, max_drawdown=None, period=252):
    """
    Calculate Calmar Ratio - annualized return divided by maximum drawdown
    
    Args:
        returns: pandas Series or numpy array of returns
        max_drawdown: pre-calculated maximum drawdown (if None, will be calculated)
        period: number of periods in a year for annualization (default: 252 for daily data)
        
    Returns:
        Calmar Ratio value
    """
    # Calculate annualized return
    annualized_return = np.mean(returns) * period
    
    # Get or calculate max drawdown
    if max_drawdown is None:
        cumulative_returns = (1 + returns).cumprod()
        max_drawdown = calculate_max_drawdown(cumulative_returns)
    
    # Avoid division by zero
    if max_drawdown == 0:
        return float('inf')  # Infinite Calmar ratio if no drawdown
    
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

def calculate_portfolio_metrics(ib, symbols=None, market_symbol='SPY', 
                               duration='1 Y', bar_size='1 day', 
                               confidence_level=0.99, risk_free_rate=0.03,
                               use_position_weights=True):
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
    
    # Get annualization factors based on bar size
    periods_per_year, sqrt_periods_per_year = get_annualization_factor(bar_size)
    
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
    
    metrics = {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'market_total_return': market_total_return,
        'market_annualized_return': market_annualized_return,
        'volatility': calculate_volatility(portfolio_returns, True, periods_per_year),
        'beta': beta,
        'alpha': calculate_alpha(portfolio_returns, market_returns, risk_free_rate, beta),
        'historical_var_pct': var_pct,
        'historical_var_amount': var_amount,
        'parametric_var_pct': param_var_pct,
        'parametric_var_amount': param_var_amount,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': calculate_sharpe_ratio(portfolio_returns, risk_free_rate, True, periods_per_year),
        'calmar_ratio': calculate_calmar_ratio(portfolio_returns, max_drawdown, periods_per_year)
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
            print(f"Volatility (annualized): {metrics['volatility']:.4f}")
            print(f"Beta: {metrics['beta']:.4f}")
            print(f"Alpha: {metrics['alpha']:.4f}")
            print(f"Historical VaR (99%): {metrics['historical_var_pct']:.4f} ({metrics['historical_var_amount']:.2f} USD)")
            print(f"Parametric VaR (99%): {metrics['parametric_var_pct']:.4f} ({metrics['parametric_var_amount']:.2f} USD)")
            print(f"Maximum Drawdown: {metrics['max_drawdown']:.4f}")
            print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
            print(f"Calmar Ratio: {metrics['calmar_ratio']:.4f}")
            
            print("\n📊 INDIVIDUAL STOCK METRICS\n")
            for symbol, stock_metric in metrics['stock_metrics'].items():
                print(f"{symbol}:")
                print(f"  Total Return: {stock_metric['total_return']:.2%}")
                print(f"  Annualized Return: {stock_metric['annualized_return']:.2%}")
                print(f"  Volatility: {stock_metric['volatility']:.4f}")
                print(f"  Beta: {stock_metric['beta']:.4f}")
                print(f"  Alpha: {stock_metric['alpha']:.4f}")
                print(f"  Historical VaR (99%): {stock_metric['historical_var_pct']:.4f} ({stock_metric['historical_var_amount']:.2f} USD)")
                print(f"  Parametric VaR (99%): {stock_metric['parametric_var_pct']:.4f} ({stock_metric['parametric_var_amount']:.2f} USD)")
                print(f"  Maximum Drawdown: {stock_metric['max_drawdown']:.4f}")
                print(f"  Sharpe Ratio: {stock_metric['sharpe_ratio']:.4f}")
                print(f"  Calmar Ratio: {stock_metric['calmar_ratio']:.4f}")
                print()
    
    if ib and ib.isConnected():
        ib.disconnect()