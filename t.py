from sqlalchemy import func
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Price, Ticker
from app.utils.decorators.database import with_session
from datetime import datetime
from typing import Tuple, Optional, List
from app.db.core.pull_fmp_data import FMP_API_DATA
import pandas as pd

@with_session('market')
def find_all_active_tickers(session=None) -> List[str]:
    """Find all active tickers in the database.
    """
    tickers = session.query(Ticker).filter(Ticker.is_actively_trading == True).all()
    return [ticker.ticker for ticker in tickers]

@with_session('market')
def get_ticker_timestamp_range(ticker: str, session=None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Get the first and last timestamps for a ticker in the database.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Tuple of (first_timestamp, last_timestamp) or (None, None) if no data exists
    """
    ticker = ticker.upper()

    result = session.query(
        func.min(Price.datetime).label('first'),
        func.max(Price.datetime).label('last')
    ).join(Ticker).filter(
        Ticker.ticker == ticker
    ).first()

    if result and result.first and result.last:
        return result.first, result.last

    return None, None

def get_fmp_eod_data(ticker: str, from_date: datetime, to_date: datetime):
    fmp = FMP_API_DATA()
    data = fmp.get_daily_prices_for_ticker(ticker, from_date, to_date)
    return data

if __name__ == "__main__":
    first, last = get_ticker_timestamp_range("AAPL")

    data = get_fmp_eod_data("AAPL", first, last)
    print(data['historical'])
    data_df = pd.DataFrame(data['historical'])
    print(data_df.head())
    print(data_df.tail())

    tickers = find_all_active_tickers()
    
