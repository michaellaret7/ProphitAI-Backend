from app.db.core.market_data_models import *
from app.db.core.db_config import *
from app.core.calculations.portfolio.concentration import PortfolioConcentration
import pandas as pd
from app.core.calculations.portfolio.utils import prepare_portfolio_data, format_correlation_matrix
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis

# Define the user portfolio
long_only_portfolio = {
    "AAPL": {"position": "long", "allocation": 0.07},
    "MSFT": {"position": "long", "allocation": 0.07},
    "GOOGL": {"position": "long", "allocation": 0.06},
    "AMZN": {"position": "long", "allocation": 0.06},
    "NVDA": {"position": "long", "allocation": 0.06},
    "TSLA": {"position": "long", "allocation": 0.05},
    "JPM": {"position": "long", "allocation": 0.05},
    "V": {"position": "long", "allocation": 0.05},
    "JNJ": {"position": "long", "allocation": 0.05},
    "PG": {"position": "long", "allocation": 0.05},
    "XOM": {"position": "long", "allocation": 0.05},
    "UNH": {"position": "long", "allocation": 0.05},
    "HD": {"position": "long", "allocation": 0.05},
    "SPY": {"position": "long", "allocation": 0.06},
    "QQQ": {"position": "long", "allocation": 0.05},
    "IWM": {"position": "long", "allocation": 0.04},
    "EFA": {"position": "long", "allocation": 0.04},
    "EEM": {"position": "long", "allocation": 0.04},
}

long_short_portfolio = {
    "AAPL": {"position": "long", "allocation": 0.05},
    "MSFT": {"position": "long", "allocation": 0.05},
    "GOOGL": {"position": "long", "allocation": 0.05},
    "AMZN": {"position": "long", "allocation": 0.05},
    "NVDA": {"position": "long", "allocation": 0.05},
    "PG": {"position": "long", "allocation": 0.04},
    "JNJ": {"position": "long", "allocation": 0.04},
    "XOM": {"position": "long", "allocation": 0.04},
    "JPM": {"position": "long", "allocation": 0.04},
    "SPY": {"position": "long", "allocation": 0.05},
    
    "TSLA": {"position": "short", "allocation": 0.04},
    "NFLX": {"position": "short", "allocation": 0.04},
    "ZM": {"position": "short", "allocation": 0.03},
    "COIN": {"position": "short", "allocation": 0.03},
    "RIVN": {"position": "short", "allocation": 0.03},
    "MARA": {"position": "short", "allocation": 0.03},
    "GME": {"position": "short", "allocation": 0.03},
    "AMC": {"position": "short", "allocation": 0.03},
    "ARKK": {"position": "short", "allocation": 0.04},
    "IWM": {"position": "short", "allocation": 0.03},
    "EEM": {"position": "short", "allocation": 0.03},
    "BYND": {"position": "short", "allocation": 0.02}
}

etf_hedge_portfolio = {
    "JPM": {"position": "long", "allocation": 0.07},
    "BAC": {"position": "long", "allocation": 0.06},
    "MS": {"position": "long", "allocation": 0.06},
    "GS": {"position": "long", "allocation": 0.06},
    "WFC": {"position": "long", "allocation": 0.05},
    "C": {"position": "long", "allocation": 0.05},
    "PNC": {"position": "long", "allocation": 0.05},
    "SCHW": {"position": "long", "allocation": 0.05},
    "USB": {"position": "long", "allocation": 0.05},
    "BK": {"position": "long", "allocation": 0.05},

    "XLF": {"position": "short", "allocation": 0.20},
    "KBE": {"position": "short", "allocation": 0.10},
    "KRE": {"position": "short", "allocation": 0.10}
}

dividend_portfolio = {
    "VYM": {"position": "long", "allocation": 0.10},
    "SCHD": {"position": "long", "allocation": 0.10},
    "DVY": {"position": "long", "allocation": 0.08},
    "HDV": {"position": "long", "allocation": 0.08},
    "NOBL": {"position": "long", "allocation": 0.08},
    "SPYD": {"position": "long", "allocation": 0.08},
    "SDY": {"position": "long", "allocation": 0.08},
    "FDL": {"position": "long", "allocation": 0.08},
    "DHS": {"position": "long", "allocation": 0.08},
    "VIG": {"position": "long", "allocation": 0.08},
    "IDV": {"position": "long", "allocation": 0.08},
    "EFAD": {"position": "long", "allocation": 0.08}
}

def concentration(portfolio_dict: dict):
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
    return format_correlation_matrix(CorrelationAnalysis.correlation_matrix(returns_df))
