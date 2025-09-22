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

@with_price_data(lookback_days=252, include_dividends=False)
def get_weekly_returns(ticker: str, price_data=None, **kwargs):
    """Get weekly returns for the last year for a given ticker."""
    
    # Resample to weekly and calculate returns
    weekly_prices = price_data.resample('W').last()
    weekly_returns = weekly_prices.pct_change().dropna()
    
    # Convert to dictionary with string dates and format as percentages
    return {
        "ticker": ticker,
        "weekly_returns": {str(date.date()): f"{round(ret * 100, 2)}%" for date, ret in weekly_returns.items()},
        "total_weeks": len(weekly_returns),
        "average_weekly_return": f"{round(weekly_returns.mean() * 100, 2)}%" if not weekly_returns.empty else "0%"
    }

@with_session('market')
def get_eligible_tickers(industry: str, session=None):
    """Get the eligible tickers for a given industry."""
    industry = industry.lower()
    tickers = session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > 600_000_000).all()
    return [ticker.ticker for ticker in tickers]

@with_session('market')
def get_base_ticker_info(tickers: List[str], session=None):
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
    
    return result


if __name__ == "__main__":
    print(get_weekly_returns("AAPL"))