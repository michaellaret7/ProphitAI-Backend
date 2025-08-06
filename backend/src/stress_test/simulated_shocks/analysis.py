"""
Analysis functions for stress test simulations.
This module contains functions for analyzing stress test results including
industry returns, contribution analysis, and performance metrics.
"""

import pandas as pd
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Ticker


def get_industry_mapping(tickers):
    """
    Get industry mapping for a list of tickers.
    
    Parameters:
    - tickers: List of ticker symbols
    
    Returns:
    - dict: Mapping of ticker to industry
    """
    session = MarketSession()
    tickers_db = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
    session.close()
    
    industry_map = {ticker.ticker: ticker.industry for ticker in tickers_db}
    return industry_map


def industry_returns_analysis(scenario_results):
    """
    Calculate returns per industry from scenario results.
    
    Parameters:
    - scenario_results: Dict returned from multi_factor_market_shock
    
    Returns:
    - dict: Industry returns as percentages
    """
    df = scenario_results['position_details'].copy()
    
    # Get industry mapping
    tickers = df['ticker'].tolist()
    industry_map = get_industry_mapping(tickers)
    df['industry'] = df['ticker'].map(industry_map)
    
    # Group by industry and calculate total PnL
    industry_returns = df.groupby('industry')['pnl'].sum()
    
    # Convert to percentage and format
    industry_returns_dict = {}
    for industry, pnl in industry_returns.items():
        industry_returns_dict[industry] = f"{round(float(pnl) * 100, 2)}%"
    
    return industry_returns_dict


def contribution_analysis(scenario_results):
    """
    Perform contribution analysis on scenario results.
    
    Parameters:
    - scenario_results: Dict returned from multi_factor_market_shock
    
    Returns:
    - dict: Analysis results including position ranking, concentration metrics, and long/short attribution
    """
    df = scenario_results['position_details'].copy()
    
    # 1. Position P&L Impact: Rank all positions by absolute P&L contribution
    df['abs_pnl'] = df['pnl'].abs()
    position_ranking = df.sort_values('abs_pnl', ascending=False)[['ticker', 'position', 'pnl', 'abs_pnl']]
    
    # 2. Concentration Metric: Calculate % of total loss from top positions
    total_abs_loss = float(df['abs_pnl'].sum())
    top_3_loss = float(position_ranking.head(3)['abs_pnl'].sum())
    top_5_loss = float(position_ranking.head(5)['abs_pnl'].sum())
    top_10_loss = float(position_ranking.head(10)['abs_pnl'].sum())
    
    concentration_metrics = {
        'top_3_concentration': f"{round(float((top_3_loss / total_abs_loss) * 100), 2)}%" if total_abs_loss != 0 else "0.0%",
        'top_5_concentration': f"{round(float((top_5_loss / total_abs_loss) * 100), 2)}%" if total_abs_loss != 0 else "0.0%",
        'top_10_concentration': f"{round(float((top_10_loss / total_abs_loss) * 100), 2)}%" if total_abs_loss != 0 else "0.0%"
    }
    
    # 3. Long vs Short Attribution: Sum P&L separately for long book vs short book
    long_pnl = float(df[df['position'] == 'long']['pnl'].sum())
    short_pnl = float(df[df['position'] == 'short']['pnl'].sum())
    total_pnl = float(df['pnl'].sum())
    total_abs_pnl = float(df['abs_pnl'].sum())
    
    # Calculate contribution as % of total absolute P&L for consistent interpretation
    attribution = {
        'long_book_pnl': f"{round(long_pnl * 100, 2)}%",
        'short_book_pnl': f"{round(short_pnl * 100, 2)}%",
        'total_pnl': f"{round(total_pnl * 100, 2)}%",
        'long_contribution_pct': f"{round(float((abs(long_pnl) / total_abs_pnl) * 100), 2)}%" if total_abs_pnl != 0 else "0.0%",
        'short_contribution_pct': f"{round(float((abs(short_pnl) / total_abs_pnl) * 100), 2)}%" if total_abs_pnl != 0 else "0.0%"
    }
    
    return {
        'concentration_metrics': concentration_metrics,
        'long_short_attribution': attribution
    }


def performance_analysis(scenario_results):
    """
    Perform performance analysis on scenario results.
    
    Parameters:
    - scenario_results: Dict returned from multi_factor_market_shock
    
    Returns:
    - dict: Performance metrics including beta exposures and P&L rankings
    """
    df = scenario_results['position_details'].copy()

    # --- 1. Top 5 Tickers by Beta Exposure ---
    beta_columns = [col for col in df.columns if col.startswith('beta_')]
    
    # Melt the DataFrame to have one row per ticker-beta combination
    melted_betas = df.melt(id_vars=['ticker'], value_vars=beta_columns, var_name='beta_factor', value_name='beta_value')
    
    # Get the top 5 highest beta values across all factors
    top_5_betas = melted_betas.nlargest(5, 'beta_value')
    top_5_betas['beta_value'] = top_5_betas['beta_value'].round(4)
    
    top_betas = top_5_betas.to_dict('records')

    # --- 2. Top & Bottom 3 Tickers by P&L ---
    top_3_pnl_df = df.nlargest(3, 'pnl')[['ticker', 'position', 'pnl']].copy()
    top_3_pnl_df['ticker_with_position'] = top_3_pnl_df.apply(lambda row: f"{row['ticker']} ({row['position'][0].upper()})", axis=1)
    top_3_pnl_df['pnl'] = top_3_pnl_df['pnl'].apply(lambda x: f"{round(x * 100, 2)}%")
    top_3_pnl = top_3_pnl_df[['ticker_with_position', 'pnl']].to_dict('records')

    bottom_3_pnl_df = df.nsmallest(3, 'pnl')[['ticker', 'position', 'pnl']].copy()
    bottom_3_pnl_df['ticker_with_position'] = bottom_3_pnl_df.apply(lambda row: f"{row['ticker']} ({row['position'][0].upper()})", axis=1)
    bottom_3_pnl_df['pnl'] = bottom_3_pnl_df['pnl'].apply(lambda x: f"{round(x * 100, 2)}%")
    bottom_3_pnl = bottom_3_pnl_df[['ticker_with_position', 'pnl']].to_dict('records')

    # --- 3. Top & Bottom 3 Tickers by Total Stock Return ---
    top_3_return_df = df.nlargest(3, 'total_stock_return')[['ticker', 'total_stock_return']].copy()
    top_3_return_df['total_stock_return'] = top_3_return_df['total_stock_return'].apply(lambda x: f"{round(x * 100, 2)}%")
    top_3_return = top_3_return_df.to_dict('records')

    bottom_3_return_df = df.nsmallest(3, 'total_stock_return')[['ticker', 'total_stock_return']].copy()
    bottom_3_return_df['total_stock_return'] = bottom_3_return_df['total_stock_return'].apply(lambda x: f"{round(x * 100, 2)}%")
    bottom_3_return = bottom_3_return_df.to_dict('records')
    
    performance_dict = {
        '5_highest_beta_exposures': top_betas,
        'pnl_analysis': {
            'top_3_performers': top_3_pnl,
            'bottom_3_performers': bottom_3_pnl
        },
        'return_analysis': {
            'top_3_performers': top_3_return,
            'bottom_3_performers': bottom_3_return
        }
    }
    
    return performance_dict