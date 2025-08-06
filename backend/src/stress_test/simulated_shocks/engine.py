import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers

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

