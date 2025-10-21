"""Portfolio-level market risk scoring."""

from .market import calculate_market_risk
import pandas as pd
import numpy as np


def calculate_portfolio_market_risk(portfolio, price_data_map, market_data, lookback_days=252):
    """
    Calculate market risk for portfolio using weighted returns.

    Args:
        portfolio: Dict of {ticker: allocation} e.g. {'AAPL': 0.4, 'MSFT': 0.6}
        price_data_map: Dict of {ticker: DataFrame with 'close' column}
        market_data: DataFrame with 'close' column for benchmark (SPY)
        lookback_days: Days of history (default 252)

    Returns:
        Dict with market_risk_score and metrics
    """
    # Validate allocations sum to 1.0
    total = sum(portfolio.values())
    if not np.isclose(total, 1.0, atol=0.01):
        return {'error': f'Allocations must sum to 1.0 (got {total:.4f})'}

    # Get returns for each ticker
    returns_dict = {}
    for ticker, allocation in portfolio.items():
        if ticker not in price_data_map or price_data_map[ticker].empty:
            return {'error': f'No data for {ticker}'}
        returns_dict[ticker] = price_data_map[ticker]['close'].pct_change().dropna()

    # Create returns DataFrame
    returns_df = pd.DataFrame(returns_dict)
    if returns_df.empty:
        return {'error': 'No overlapping data'}

    # Calculate weighted portfolio returns
    portfolio_returns = pd.Series(0.0, index=returns_df.index)
    for ticker, allocation in portfolio.items():
        portfolio_returns += returns_df[ticker] * allocation

    # Create synthetic price series (start at 100)
    portfolio_prices = (1 + portfolio_returns).cumprod() * 100
    portfolio_df = pd.DataFrame({'close': portfolio_prices})

    # Use calculate_market_risk (DRY principle)
    result = calculate_market_risk('PORTFOLIO', portfolio_df, market_data, lookback_days)

    # Add portfolio metadata
    if 'error' not in result:
        result['portfolio'] = portfolio
        result['num_holdings'] = len(portfolio)

    return result


