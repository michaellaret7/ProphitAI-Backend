from backend.src.repositories.prophit_alts_data import get_fund_final_positions
from backend.src.db.core.db_config import ProphitAltsSession, MarketSession
from backend.src.db.core.prophit_alts_models import *
from backend.src.db.core.market_data_models import *
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_fund_landing_page_metrics(fund_name: str) -> dict:
    """
    Calculate key performance metrics for a fund.
    
    Returns:
        JSON with the following metrics:
        - ytd_return: Year-to-date return (in %)
        - gross_exposure: Sum of absolute position values (in %, can exceed 100% if leveraged)
        - net_exposure: Net long minus short exposure (in %)
        - sharpe_ratio: Risk-adjusted return ratio
        - sortino_ratio: Downside risk-adjusted return ratio
        - max_drawdown: Maximum peak-to-trough decline (in %)
        - beta: Market correlation coefficient vs SPY
        - var_95: 95% confidence Value at Risk (in %)
    """
    # Get fund positions
    session = ProphitAltsSession()
    fund = session.query(Fund).filter(Fund.fund_name == fund_name).first()
    
    if not fund:
        session.close()
        return json.dumps({"error": f"Fund '{fund_name}' not found"})
    
    fund_positions = session.query(FundFinalPosition).filter(FundFinalPosition.fund_id == fund.id).all()
    fund_positions = [serialize_sqlalchemy_obj(position) for position in fund_positions]
    session.close()
    
    if not fund_positions:
        return json.dumps({"error": "No positions found for fund"})
    
    # Extract tickers and weights
    tickers = []
    weights = {}
    long_exposure = 0.0   # Sum of long positions
    short_exposure = 0.0  # Sum of short positions (as positive values)
    
    for position in fund_positions:
        ticker = position['ticker_name']
        # Portfolio allocation is already in decimal form (e.g., 0.25 = 25%)
        allocation = float(position['portfolio_allocation'])
        
        tickers.append(ticker)
        
        # Handle long/short positions
        # Extract the enum value from the serialized format
        position_raw = position.get('position', 'LONG')
        
        # Handle both enum string format and plain strings
        if 'SHORT' in str(position_raw).upper():
            weights[ticker] = -allocation  # Negative weight for shorts
            short_exposure += allocation   # Track short exposure (as positive)
        else:  # LONG position
            weights[ticker] = allocation   # Positive weight for longs
            long_exposure += allocation    # Track long exposure
    
    # Calculate gross and net exposure correctly
    # Gross = Long + Short (both as absolute values)
    # Net = Long - Short (directional exposure)
    # Note: If gross == net, the fund has no short positions (100% long)
    gross_exposure = long_exposure + short_exposure  # Sum of absolute values
    net_exposure = long_exposure - short_exposure    # Long minus short
    
    # Store original exposures before normalization (for reporting actual leverage)
    original_gross_exposure = gross_exposure
    original_net_exposure = net_exposure
    
    # Normalize weights to sum to 100% if they don't already
    # This handles leveraged positions (e.g., 250% gross exposure = 2.5x leverage)
    total_weight = sum(abs(w) for w in weights.values())
    if total_weight > 0 and abs(total_weight - 1.0) > 0.01:  # If not close to 100%
        # Normalize weights for return calculations only
        # Original exposures are preserved to show actual leverage
        for ticker in weights:
            weights[ticker] = weights[ticker] / total_weight
    
    # Add SPY for beta calculation
    if 'SPY' not in tickers:
        tickers.append('SPY')
    
    # Fetch price data for last 504 trading days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=504)  # ~504 trading days
    
    # Format dates for the function
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Fetch all price data at once
    price_data = fetch_bulk_price_data_for_tickers(
        tickers, 
        start_date_str, 
        end_date_str, 
        frequency='daily'
    )
    
    # Calculate portfolio returns
    returns_data = pd.DataFrame()
    for ticker, prices in price_data.items():
        if not prices.empty:
            returns_data[ticker] = prices.pct_change()
    
    returns_data = returns_data.dropna()
    
    if returns_data.empty:
        return json.dumps({"error": "Insufficient price data"})
    
    # Calculate portfolio returns based on weights
    portfolio_returns = pd.Series(0, index=returns_data.index)
    for ticker, weight in weights.items():
        if ticker in returns_data.columns:
            portfolio_returns += returns_data[ticker] * weight
    
    # Calculate metrics
    metrics = {}
    
    # 1. YTD Return (in percentage terms)
    current_year = datetime.now().year
    ytd_returns = portfolio_returns[portfolio_returns.index.year == current_year]
    if not ytd_returns.empty:
        ytd_return = (1 + ytd_returns).prod() - 1
        metrics['ytd_return'] = round(ytd_return * 100, 2)  # Convert to percentage (e.g., 0.1014 -> 10.14%)
    else:
        metrics['ytd_return'] = 0.0
    
    # 2. Gross and Net Exposure (already in percentage terms)
    # Database values are in decimal form (0.1 = 10%), so multiply by 100 for display
    metrics['gross_exposure'] = round(original_gross_exposure * 100, 2)  # Convert to percentage
    metrics['net_exposure'] = round(original_net_exposure * 100, 2)      # Convert to percentage
    
    # 3. Annualized volatility
    trading_days = 252
    annual_volatility = portfolio_returns.std() * np.sqrt(trading_days)
    
    # 4. Calculate annualized return more accurately
    # Use compound annual growth rate (CAGR) from cumulative returns
    cumulative_return = (1 + portfolio_returns).prod() - 1
    n_days = len(portfolio_returns)
    years = n_days / trading_days
    
    if years > 0 and cumulative_return > -1:
        annualized_return = (1 + cumulative_return) ** (1/years) - 1
    else:
        # Fallback to simple annualization
        annualized_return = portfolio_returns.mean() * trading_days
    
    # Sharpe Ratio (assuming 2% risk-free rate)
    risk_free_rate = 0.02
    sharpe_ratio = (annualized_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
    metrics['sharpe_ratio'] = round(sharpe_ratio, 3)
    
    # 5. Sortino Ratio
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_deviation = downside_returns.std() * np.sqrt(trading_days)
    sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
    metrics['sortino_ratio'] = round(sortino_ratio, 3)
    
    # 6. Maximum Drawdown
    cumulative_returns = (1 + portfolio_returns).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    metrics['max_drawdown'] = round(max_drawdown * 100, 2)  # as percentage
    
    # 7. Beta (vs SPY)
    if 'SPY' in returns_data.columns:
        # Calculate beta using covariance
        covariance = portfolio_returns.cov(returns_data['SPY'])
        spy_variance = returns_data['SPY'].var()
        beta = covariance / spy_variance if spy_variance > 0 else 0
        metrics['beta'] = round(beta, 3)
    else:
        metrics['beta'] = None
    
    # 8. VaR (95% confidence level)
    var_95 = np.percentile(portfolio_returns, 5)  # 5th percentile for 95% confidence
    var_95_annual = var_95 * np.sqrt(trading_days)  # Annualized
    metrics['var_95'] = round(var_95_annual * 100, 2)  # as percentage
    
    return json.dumps(metrics)

if __name__ == "__main__":
    print(get_fund_landing_page_metrics('consumer_staples_fund'))
