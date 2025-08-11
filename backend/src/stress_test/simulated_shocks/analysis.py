"""
Analysis functions for stress test simulations.
This module contains functions for analyzing stress test results including
industry returns, contribution analysis, and performance metrics.
"""

import pandas as pd
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Ticker
from backend.src.stress_test.simulated_shocks.scenarios import historical_scenarios
from backend.src.stress_test.simulated_shocks.engine import run_stress_test_engine


def industry_returns_analysis(scenario_results, portfolio_dict=None):
    """
    Calculate weighted average returns per industry from scenario results.
    
    Parameters:
    - scenario_results: Dict returned from multi_factor_market_shock
    - portfolio_dict: Optional dict with conviction weights for weighted average calculation
    
    Returns:
    - dict: Industry returns as percentages (weighted average if portfolio_dict provided)
    """
    df = scenario_results['position_details'].copy()

    session = MarketSession()
    tickers_db = session.query(Ticker).filter(Ticker.ticker.in_(df['ticker'].tolist())).all()
    session.close()
    
    industry_map = {ticker.ticker: ticker.industry for ticker in tickers_db}

    df['industry'] = df['ticker'].map(industry_map)
    
    if portfolio_dict:
        # Add conviction weights to dataframe
        df['conviction'] = df['ticker'].map(lambda x: portfolio_dict.get(x, {}).get('conviction', 0))
        
        # Calculate weighted return per industry
        industry_groups = df.groupby('industry')
        industry_returns_dict = {}
        
        for industry, group in industry_groups:
            # Calculate weighted average return for the industry
            total_weight = group['conviction'].sum()
            if total_weight > 0:
                weighted_return = (group['pnl'] * group['conviction']).sum() / total_weight
                industry_returns_dict[industry] = f"{round(float(weighted_return) * 100, 2)}%"
            else:
                industry_returns_dict[industry] = "0.00%"
    else:
        # Simple average return per industry if no weights provided
        industry_returns = df.groupby('industry')['pnl'].mean()
        
        # Convert to percentage and format
        industry_returns_dict = {}
        for industry, pnl in industry_returns.items():
            industry_returns_dict[industry] = f"{round(float(pnl) * 100, 2)}%"
    
    return industry_returns_dict

def contribution_analysis(scenario_results, portfolio_dict=None):
    """
    Perform contribution analysis on scenario results.
    
    Parameters:
    - scenario_results: Dict returned from multi_factor_market_shock
    - portfolio_dict: Optional dict with conviction weights for weighted average calculation
    
    Returns:
    - dict: Analysis results including position ranking, concentration metrics, and long/short attribution
    """
    df = scenario_results['position_details'].copy()
    
    # Add conviction weights if portfolio_dict is provided
    if portfolio_dict:
        df['conviction'] = df['ticker'].map(lambda x: portfolio_dict.get(x, {}).get('conviction', 0))
    else:
        # Assume equal weights if no portfolio_dict provided
        df['conviction'] = 1.0 / len(df)
    
    # Calculate weighted PnL
    df['weighted_pnl'] = df['pnl'] * df['conviction']
    df['weighted_abs_pnl'] = df['weighted_pnl'].abs()
    
    # 1. Position P&L Impact: Rank all positions by absolute weighted P&L contribution
    df['abs_pnl'] = df['pnl'].abs()
    position_ranking = df.sort_values('weighted_abs_pnl', ascending=False)[['ticker', 'position', 'pnl', 'weighted_pnl', 'weighted_abs_pnl']]
    
    # 2. Concentration Metric: Calculate % of total loss from top positions (using weighted values)
    total_weighted_abs_loss = float(df['weighted_abs_pnl'].sum())
    top_3_loss = float(position_ranking.head(3)['weighted_abs_pnl'].sum())
    top_5_loss = float(position_ranking.head(5)['weighted_abs_pnl'].sum())
    top_10_loss = float(position_ranking.head(10)['weighted_abs_pnl'].sum())
    
    concentration_metrics = {
        'top_3_concentration': f"{round(float((top_3_loss / total_weighted_abs_loss) * 100), 2)}%" if total_weighted_abs_loss != 0 else "0.0%",
        'top_5_concentration': f"{round(float((top_5_loss / total_weighted_abs_loss) * 100), 2)}%" if total_weighted_abs_loss != 0 else "0.0%",
        'top_10_concentration': f"{round(float((top_10_loss / total_weighted_abs_loss) * 100), 2)}%" if total_weighted_abs_loss != 0 else "0.0%"
    }
    
    # 3. Long vs Short Attribution: Use weighted PnLs
    long_weighted_pnl = float(df[df['position'] == 'long']['weighted_pnl'].sum())
    short_weighted_pnl = float(df[df['position'] == 'short']['weighted_pnl'].sum())
    total_weighted_pnl = float(df['weighted_pnl'].sum())
    total_weighted_abs_pnl = float(df['weighted_abs_pnl'].sum())
    
    # Calculate contribution as % of total absolute P&L for consistent interpretation
    attribution = {
        'long_book_pnl': f"{round(long_weighted_pnl * 100, 2)}%",
        'short_book_pnl': f"{round(short_weighted_pnl * 100, 2)}%",
        'total_pnl': f"{round(total_weighted_pnl * 100, 2)}%",
        'long_contribution_pct': f"{round(float((abs(long_weighted_pnl) / total_weighted_abs_pnl) * 100), 2)}%" if total_weighted_abs_pnl != 0 else "0.0%",
        'short_contribution_pct': f"{round(float((abs(short_weighted_pnl) / total_weighted_abs_pnl) * 100), 2)}%" if total_weighted_abs_pnl != 0 else "0.0%"
    }
    
    return {
        'concentration_metrics': concentration_metrics,
        'long_short_attribution': attribution
    }

def performance_analysis(scenario_results, portfolio_dict=None):
    """
    Perform performance analysis on scenario results.
    
    Parameters:
    - scenario_results: Dict returned from multi_factor_market_shock
    - portfolio_dict: Optional dict with conviction weights for weighted P&L calculation
    
    Returns:
    - dict: Performance metrics including beta exposures and P&L rankings
    """
    df = scenario_results['position_details'].copy()
    
    # Add conviction weights if portfolio_dict is provided
    if portfolio_dict:
        df['conviction'] = df['ticker'].map(lambda x: portfolio_dict.get(x, {}).get('conviction', 0))
        df['weighted_pnl'] = df['pnl'] * df['conviction']
    else:
        # If no weights, use raw PnL
        df['weighted_pnl'] = df['pnl']

    # --- 1. Top 5 Tickers by Beta Exposure ---
    beta_columns = [col for col in df.columns if col.startswith('beta_')]
    
    # Melt the DataFrame to have one row per ticker-beta combination
    melted_betas = df.melt(id_vars=['ticker'], value_vars=beta_columns, var_name='beta_factor', value_name='beta_value')
    
    # Get the top 5 highest beta values across all factors
    top_5_betas = melted_betas.nlargest(5, 'beta_value')
    top_5_betas['beta_value'] = top_5_betas['beta_value'].round(4)
    
    top_betas = top_5_betas.to_dict('records')

    # --- 2. Top & Bottom 3 Positions by Portfolio P&L Impact (using weighted PnL) ---
    # Sort by weighted PnL to show actual portfolio impact
    top_3_pnl_df = df.nlargest(3, 'weighted_pnl')[['ticker', 'position', 'pnl', 'weighted_pnl']].copy()
    top_3_pnl_df['ticker_with_position'] = top_3_pnl_df.apply(lambda row: f"{row['ticker']} ({row['position'][0].upper()})", axis=1)
    # Display the weighted PnL for actual portfolio impact
    top_3_pnl_df['portfolio_impact'] = top_3_pnl_df['weighted_pnl'].apply(lambda x: f"{round(x * 100, 2)}%")
    top_3_pnl = top_3_pnl_df[['ticker_with_position', 'portfolio_impact']].rename(columns={'portfolio_impact': 'pnl'}).to_dict('records')

    bottom_3_pnl_df = df.nsmallest(3, 'weighted_pnl')[['ticker', 'position', 'pnl', 'weighted_pnl']].copy()
    bottom_3_pnl_df['ticker_with_position'] = bottom_3_pnl_df.apply(lambda row: f"{row['ticker']} ({row['position'][0].upper()})", axis=1)
    # Display the weighted PnL for actual portfolio impact
    bottom_3_pnl_df['portfolio_impact'] = bottom_3_pnl_df['weighted_pnl'].apply(lambda x: f"{round(x * 100, 2)}%")
    bottom_3_pnl = bottom_3_pnl_df[['ticker_with_position', 'portfolio_impact']].rename(columns={'portfolio_impact': 'pnl'}).to_dict('records')

    # --- 3. Top & Bottom 3 Tickers by Stock Price Movement ---
    top_3_return_df = df.nlargest(3, 'total_stock_return')[['ticker', 'position', 'total_stock_return']].copy()
    # Add position type to clarify impact
    top_3_return_df['ticker_with_position'] = top_3_return_df.apply(lambda row: f"{row['ticker']} ({row['position'][0].upper()})", axis=1)
    top_3_return_df['stock_movement'] = top_3_return_df['total_stock_return'].apply(lambda x: f"{round(x * 100, 2)}%")
    top_3_return = top_3_return_df[['ticker_with_position', 'stock_movement']].rename(columns={'stock_movement': 'total_stock_return'}).to_dict('records')

    bottom_3_return_df = df.nsmallest(3, 'total_stock_return')[['ticker', 'position', 'total_stock_return']].copy()
    # Add position type to clarify impact
    bottom_3_return_df['ticker_with_position'] = bottom_3_return_df.apply(lambda row: f"{row['ticker']} ({row['position'][0].upper()})", axis=1)
    bottom_3_return_df['stock_movement'] = bottom_3_return_df['total_stock_return'].apply(lambda x: f"{round(x * 100, 2)}%")
    bottom_3_return = bottom_3_return_df[['ticker_with_position', 'stock_movement']].rename(columns={'stock_movement': 'total_stock_return'}).to_dict('records')
    
    performance_dict = {
        '5_highest_beta_exposures': top_betas,
        'portfolio_pnl_impact': {
            'top_3_gainers': top_3_pnl,
            'top_3_losers': bottom_3_pnl,
            'note': 'Shows weighted P&L accounting for position size and direction (long/short)'
        },
        'stock_price_movements': {
            'top_3_gainers': top_3_return,
            'top_3_decliners': bottom_3_return,
            'note': 'Shows actual stock price changes (positive = up, negative = down)'
        }
    }
    
    return performance_dict


    