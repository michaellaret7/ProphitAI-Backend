from app.db.core.market_data_models import *
from app.db.core.db_config import *
from app.core.calculations.portfolio.concentration import PortfolioConcentration
import pandas as pd
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis

def sector_concentration(portfolio_dict: dict):
    return {
        "industry": PortfolioConcentration(portfolio_dict).industry_concentration(),
        "sub_industry": PortfolioConcentration(portfolio_dict).sub_industry_concentration(),
        "sector": PortfolioConcentration(portfolio_dict).sector_concentration()
    }

def correlation_matrix(portfolio_dict: dict):
    """Compute pairwise correlation matrix for tickers in a portfolio dict.

    Uses calculations in app.core.calculations.portfolio to stay DRY.
    """
    # Fetch bulk prices for portfolio tickers (no dividends needed for price returns)
    _, price_data, _ = prepare_portfolio_data(
        portfolio=portfolio_dict,
        lookback_days=252,
        include_dividends=False
    )

    if not price_data:
        return pd.DataFrame()

    # Build returns DataFrame for portfolio tickers
    returns_map = {}
    for ticker in portfolio_dict.keys():
        series = price_data.get(ticker)
        if series is not None and not series.empty:
            returns_map[ticker] = ReturnsCalculator.daily_price_returns(series)

    if not returns_map:
        return pd.DataFrame()

    returns_df = pd.DataFrame(returns_map).dropna(how='any')
    if returns_df.empty:
        return pd.DataFrame()

    # Delegate correlation computation to shared calculator
    return CorrelationAnalysis.correlation_matrix(returns_df)
