import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backend.src.repositories.price_data import get_price_data_daily, fetch_bulk_price_data_for_tickers

def calculate_betas_for_portfolio(portfolio_tickers: list, benchmark_ticker: str, returns_map: dict):
    """
    Calculate betas for multiple tickers against a benchmark.
    
    Parameters:
    - portfolio_tickers: List of portfolio ticker symbols
    - benchmark_ticker: Benchmark ticker symbol
    - returns_map: Dictionary mapping tickers to their return series
    
    Returns:
    - dict: Mapping of ticker to beta value
    """
    betas = {}
    benchmark_returns = returns_map.get(benchmark_ticker)
    
    if benchmark_returns is None:
        print(f"Warning: Could not get returns for benchmark {benchmark_ticker}.")
        return {ticker: 1.0 for ticker in portfolio_tickers}
    
    for ticker in portfolio_tickers:
        ticker_returns = returns_map.get(ticker)
        if ticker_returns is not None:
            combined_returns = pd.concat([ticker_returns, benchmark_returns], axis=1, join='inner')
            combined_returns.columns = [ticker, benchmark_ticker]
            
            if len(combined_returns) > 2 and combined_returns[benchmark_ticker].var() != 0:
                covariance = combined_returns[ticker].cov(combined_returns[benchmark_ticker])
                variance = combined_returns[benchmark_ticker].var()
                betas[ticker] = covariance / variance
            else:
                betas[ticker] = 1.0
        else:
            betas[ticker] = 1.0
    
    return betas

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
    ticker_returns = ticker_prices.pct_change().dropna()
    benchmark_returns = benchmark_prices.pct_change().dropna()

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

def simulated_market_shock(portfolio_df, market_shock=-0.10, benchmark_ticker=None, period_days=730):
    """
    Simple stress test: calculates beta and applies market_shock.
    
    Parameters:
    - portfolio_df: DataFrame with ['ticker', 'position', 'allocation']
    - market_shock: Market move (e.g., -0.10 for -10%)
    - benchmark_ticker: The benchmark to calculate beta against.
    - period_days (int): The number of past days to use for the beta calculation.
    
    Returns:
    - DataFrame with P&L for each position
    """
    
    df = portfolio_df.copy()
    tickers_to_fetch = df['ticker'].tolist()
    if benchmark_ticker and benchmark_ticker not in tickers_to_fetch:
        tickers_to_fetch.append(benchmark_ticker)
        
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Use the new helper function to fetch price data
    price_data_map = fetch_bulk_price_data_for_tickers(tickers_to_fetch, start_date_str, end_date_str, frequency='daily')
    
    # Convert prices to returns
    returns_map = {ticker: prices.pct_change().dropna() for ticker, prices in price_data_map.items()}
    
    # Use the new helper function to calculate betas
    if benchmark_ticker:
        betas = calculate_betas_for_portfolio(df['ticker'].tolist(), benchmark_ticker, returns_map)
    else:
        betas = {ticker: 1.0 for ticker in df['ticker']}
    
    df['beta'] = df['ticker'].map(betas)
    df['beta'] = df['beta'].fillna(1.0)
    
    # Calculate stock return: beta × market_shock
    df['stock_return'] = df['beta'] * market_shock
    
    # Calculate P&L (flip sign for shorts)
    df['position_multiplier'] = df['position'].map({'long': 1, 'short': -1})
    df['pnl'] = df['stock_return'] * df['position_multiplier'] * df['allocation']
    
    # Summary
    total_pnl = df['pnl'].sum()
    
    # Calculate SPY P&L
    if benchmark_ticker == 'SPY':
        spy_pnl = market_shock
    else:
        # Calculate SPY beta if not already in betas
        if 'SPY' in returns_map and benchmark_ticker in returns_map:
            spy_betas = calculate_betas_for_portfolio(['SPY'], benchmark_ticker, returns_map)
            spy_pnl = spy_betas.get('SPY', 1.0) * market_shock
        else:
            spy_pnl = market_shock
    
    print(f"\nMarket Shock: {market_shock*100:.4f}%")
    print(f"Portfolio P&L: {total_pnl*100:.4f}%")
    print(f"SPY P&L: {spy_pnl*100:.4f}%\n")
    print("Position Details:")
    print("-" * 60)
    
    for _, row in df.iterrows():
        print(f"{row['ticker']:6} {row['position']:5} β={row['beta']:.4f}  "
              f"Stock Price: {row['stock_return']*100:.4f}%  "
              f"P&L: {row['pnl']*100:.4f}%")
    
    print("-" * 60)
    print(f"{'Total Portfolio Impact:':40} {total_pnl*100:.4f}%")
    
    return df

def multi_factor_market_shock(portfolio_df, shocks: dict, period_days=730, scenario_name=None):
    """
    Calculates the portfolio impact of multiple simultaneous market shocks.

    Parameters:
    - portfolio_df (pd.DataFrame): DataFrame with ['ticker', 'position', 'allocation']
    - shocks (dict): A dictionary where keys are benchmark tickers and values are their shocks.
                     Example: {'SPY': -0.05, 'USO': 0.50}
    - period_days (int): The historical period to use for beta calculations.

    Returns:
    - pd.DataFrame: A DataFrame with detailed P&L for each position.
    """
    df = portfolio_df.copy()
    portfolio_tickers = df['ticker'].tolist()
    benchmark_tickers = list(shocks.keys())
    all_tickers_to_fetch = list(set(portfolio_tickers + benchmark_tickers))

    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Use the new helper function to fetch price data
    price_data_map = fetch_bulk_price_data_for_tickers(all_tickers_to_fetch, start_date_str, end_date_str, frequency='daily')
    
    # Convert prices to returns
    returns_map = {ticker: prices.pct_change().dropna() for ticker, prices in price_data_map.items()}
    
    df['total_stock_return'] = 0.0

    for benchmark_ticker, shock_value in shocks.items():
        # Use the helper function to calculate betas
        betas = calculate_betas_for_portfolio(portfolio_tickers, benchmark_ticker, returns_map)
        
        beta_col_name = f'beta_{benchmark_ticker}'
        df[beta_col_name] = df['ticker'].map(betas).fillna(1.0)
        df['total_stock_return'] += df[beta_col_name] * shock_value

    df['position_multiplier'] = df['position'].map({'long': 1, 'short': -1})
    df['pnl'] = df['total_stock_return'] * df['position_multiplier'] * df['allocation']

    total_pnl = df['pnl'].sum()
    
    # Calculate SPY P&L under multi-factor shocks
    if 'SPY' in shocks:
        # If SPY is directly shocked, use only its direct shock
        spy_total_return = shocks['SPY']
    else:
        # If SPY is not directly shocked, calculate its exposure to other shock factors
        spy_total_return = 0.0
        for benchmark_ticker, shock_value in shocks.items():
            spy_betas = calculate_betas_for_portfolio(['SPY'], benchmark_ticker, returns_map)
            spy_beta = spy_betas.get('SPY', 1.0)
            spy_total_return += spy_beta * shock_value
    
    print("\n--- Multi-Factor Market Shock Analysis ---")
    print("Shocks Applied:")
    for factor, shock in shocks.items():
        print(f"- {factor}: {shock*100:.2f}%")
    
    print(f"\nTotal Portfolio P&L: {total_pnl*100:.4f}%")
    print(f"SPY P&L: {spy_total_return*100:.4f}%\n")
    print("Position Details:")
    print("-" * 80)
    
    for _, row in df.iterrows():
        beta_str = " ".join([f"β_{b.split('_')[-1]}={row[b]:.2f}" for b in df.columns if b.startswith('beta_')])
        print(f"{row['ticker']:6} {row['position']:5} {beta_str} | "
              f"Stock Return: {row['total_stock_return']*100:6.2f}% | "
              f"P&L: {row['pnl']*100:6.4f}%")
    
    print("-" * 80)
    print(f"{'Total Portfolio Impact:':65} {total_pnl*100:6.4f}%")
    
    return {
        'scenario_name': scenario_name,
        'scenario_etf_moves': shocks,
        'total_portfolio_pnl': total_pnl,
        'spy_pnl': spy_total_return,
        'position_details': df
    }

