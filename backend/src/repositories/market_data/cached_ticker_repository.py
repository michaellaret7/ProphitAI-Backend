from functools import lru_cache
import logging
from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository
from datetime import datetime
from backend.src.utils.determine_etf import is_etf_ticker

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1000)
def get_cached_ticker_data(ticker, start_date, end_date, interval):
    """
    Cached function to fetch ticker data. This ensures that each ticker's data
    is only fetched once regardless of how many times it's requested.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date for data (must be hashable, use date string)
        end_date: End date for data (must be hashable, use date string)
        interval: Data interval (e.g., "1d")
    
    Returns:
        DataFrame with price data or None if no data available
    """

    
    # Convert string dates back to datetime objects
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    if is_etf_ticker(ticker):
        etf_data_repo = ETFPriceDataRepository()
        data = etf_data_repo.fetch_etf_price_data(ticker, start_date=start_dt, end_date=end_dt, interval=interval)
    else:
        equity_data_repo = EquityPriceDataRepository()
        data = equity_data_repo.fetch_equity_price_data(ticker, start_date=start_dt, end_date=end_dt, interval=interval)
    
    logger.info(f"Fetched data for {ticker} from API (cached for future use)")
    return data