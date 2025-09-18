from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.models.portfolio_models import PortfolioInput
from typing import Dict

def calculate_portfolio_beta_vs_index(
    portfolio_dict: PortfolioInput | Dict[str, Dict], 
    lookback_days: int = 252,
    index_ticker: str = None,
) -> float:
    """
    Calculate CAPM beta for a long/short portfolio vs index.
    
    Args:
        portfolio_dict: Dict of {ticker: {"allocation": float, "position": "long/short"}}
        lookback_days: Number of days of historical data to use
    
    Returns:
        Portfolio beta vs index
    """
    portfolio_dict = canonical_portfolio(portfolio_dict)
    
    # Use utility functions to get portfolio returns
    portfolio_returns, _ = get_portfolio_returns(
        portfolio=portfolio_dict,
        lookback_days=lookback_days + 50,  # Buffer for returns calc
        use_total_returns=False,  # Use price returns for beta calculation
        dropna=True
    )
    
    if portfolio_returns is None or portfolio_returns.empty:
        return float('nan')
    
    # Get index returns using utility function
    index_returns = get_benchmark_returns(
        benchmark=index_ticker,
        lookback_days=lookback_days + 50,  # Buffer for returns calc
        use_total_returns=False  # Use price returns for beta calculation
    )
    
    if index_returns is None or index_returns.empty:
        return float('nan')
    
    # Calculate and return beta
    return RiskCalculator.beta(portfolio_returns, index_returns)