from app.core.calculations.portfolio.utils import get_portfolio_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
import numpy as np

def calculate_portfolio_returns_metrics(portfolio, lookback_days=252):
    """Calculate and display simple portfolio metrics.
    
    Returns:
        dict: Contains annualized returns, volatility, and weekly cumulative returns
    """
    # Get price-only returns
    portfolio_price_returns, _ = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=False,
        dropna=True
    )
    
    # Get total returns
    portfolio_total_returns, _ = get_portfolio_returns(
        portfolio=portfolio,
        lookback_days=lookback_days,
        use_total_returns=True,
        dropna=True
    )
    
    # Calculate metrics
    ann_price_return = ReturnsCalculator.annualized_return(portfolio_price_returns, 252)
    ann_total_return = ReturnsCalculator.annualized_return(portfolio_total_returns, 252)
    ann_volatility = portfolio_total_returns.std() * np.sqrt(252)
    
    # Calculate weekly cumulative returns and convert to rounded dict
    weekly_cumulative = (1 + portfolio_total_returns).resample('W').prod() - 1
    weekly_returns = {ts.strftime('%Y-%m-%d'): round(val, 4) for ts, val in weekly_cumulative.items()}
    
    # Calculate cumulative return over period
    total_cumulative = (1 + portfolio_total_returns).prod() - 1
    
    return {
        "ann_price_return": round(ann_price_return, 4),
        "ann_total_return": round(ann_total_return, 4),
        "ann_volatility": round(ann_volatility, 4),
        "weekly_returns": weekly_returns,
        "cumulative_return": round(total_cumulative, 4)
    }