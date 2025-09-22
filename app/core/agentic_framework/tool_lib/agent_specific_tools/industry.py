import yaml
from app.core.calculations.sectors.industry import *
from app.core.calculations.sectors.sub_industry import *
from app.core.calculations.factors.growth import GrowthFactors
from app.core.calculations.factors.value import ValueFactors
from app.core.calculations.factors.momentum import MomentumFactors
from app.core.calculations.factors.quality import QualityFactors
from app.core.calculations.factors.volatility import VolatilityFactors
from app.core.calculations.core.data_service import DataService
from app.utils.decorators.database import with_session
from app.core.calculations.returns.calculator import ReturnsCalculator
from datetime import datetime, timedelta
from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker
from typing import List
from app.utils.decorators.price_data import with_price_data


@with_session('market')
def get_eligible_tickers(industry: str, session=None) -> str:
    """Get the eligible tickers for a given industry."""
    industry = industry.lower()
    tickers = session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > 600_000_000).all()
    return yaml.dump([ticker.ticker for ticker in tickers], default_flow_style=False)

@with_session('market')
def get_base_ticker_info(tickers: List[str], session=None) -> str:
    """Get the base ticker info for a given list of tickers."""
    ticker_objects = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
    
    # Convert SQLAlchemy objects to dictionaries
    result = []
    for ticker in ticker_objects:
        ticker_dict = {
            'ticker': ticker.ticker,
            'sector': ticker.sector,
            'industry': ticker.industry,
            'sub_industry': ticker.sub_industry,
            'is_etf': ticker.is_etf,
            'price': ticker.price,
            'market_cap': float(ticker.market_cap) if ticker.market_cap else None,
            'avg_volume': float(ticker.avg_volume) if ticker.avg_volume else None,
            'eps': ticker.eps,
            'pe': ticker.pe,
            'dollar_volume': float(ticker.dollar_volume) if ticker.dollar_volume else None,
        }
        result.append(ticker_dict)
    
    return yaml.dump(result, default_flow_style=False)


# Tool Schema Constants
GET_ELIGIBLE_TICKERS_DESCRIPTION = (
    "Get eligible tickers for a given industry that meet minimum market cap requirements (>$600M). "
    "Returns list of ticker symbols filtered by industry and market capitalization. "
    "Data source: Market database with ticker information and market cap filters. "
    "CRITICAL: You MUST provide the industry parameter as a valid industry name. "
    "Example: get_eligible_tickers(industry='Food Products')"
)

GET_ELIGIBLE_TICKERS_PARAMETERS = {
    "type": "object",
    "properties": {
        "industry": {
            "type": "string",
            "description": "Industry name to filter tickers by (e.g., 'Food Products', 'Beverages', 'Household Products')"
        }
    },
    "required": ["industry"],
    "additionalProperties": False
}

GET_ELIGIBLE_TICKERS_TOOL = {
    "name": "get_eligible_tickers",
    "description": GET_ELIGIBLE_TICKERS_DESCRIPTION,
    "parameters": GET_ELIGIBLE_TICKERS_PARAMETERS,
    "function": get_eligible_tickers,
}

# ------------------------------------------------------------- #

GET_BASE_TICKER_INFO_DESCRIPTION = (
    "Get comprehensive base ticker information for a list of tickers including sector, industry, market cap, volume, and fundamental metrics. "
    "Returns list of dictionaries with detailed ticker information including sector, industry, sub_industry, price, market_cap, avg_volume, eps, pe, and dollar_volume. "
    "Data source: Market database with comprehensive ticker metadata. "
    "CRITICAL: You MUST provide the tickers parameter as a list of valid stock symbols. "
    "Example: get_base_ticker_info(tickers=['AAPL', 'MSFT', 'TSLA'])"
)

GET_BASE_TICKER_INFO_PARAMETERS = {
    "type": "object",
    "properties": {
        "tickers": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^[A-Z]{1,5}$"
            },
            "description": "List of stock ticker symbols to get information for (e.g., ['AAPL', 'MSFT', 'TSLA'])",
            "minItems": 1
        }
    },
    "required": ["tickers"],
    "additionalProperties": False
}

GET_BASE_TICKER_INFO_TOOL = {
    "name": "get_base_ticker_info",
    "description": GET_BASE_TICKER_INFO_DESCRIPTION,
    "parameters": GET_BASE_TICKER_INFO_PARAMETERS,
    "function": get_base_ticker_info,
}
