from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import *
from datetime import datetime
from pandas import DataFrame
import logging

logger = logging.getLogger(__name__)

def get_price_data_15_mins(ticker: str, start_date: datetime, end_date: datetime):
    ticker = ticker.upper()
    session = MarketSession()

    query = session.query(Price).join(Ticker).filter(
        Ticker.ticker == ticker,
        Price.datetime >= start_date, 
        Price.datetime <= end_date
    ).order_by(Price.datetime)

    df = pd.read_sql(query.statement, session.bind, index_col='datetime')
    
    if df.empty:
        # Debug: Check if ticker exists
        ticker_exists = session.query(Ticker).filter(Ticker.ticker == ticker).first()
        if not ticker_exists:
            logger.debug("Ticker '%s' not found in database", ticker)
        else:
            logger.debug("Ticker '%s' exists but no price data for date range %s to %s", ticker, start_date, end_date)
    
    session.close()
    return df

def get_price_data_hourly(ticker: str, start_date: datetime, end_date: datetime):
    """
    Fetches 15-minute price data and resamples it to hourly intervals.
    """
    data_15_min_df = get_price_data_15_mins(ticker, start_date, end_date)

    if data_15_min_df.empty:
        return data_15_min_df

    # Define the aggregation logic for resampling
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }

    # Resample to hourly data. 'h' stands for hourly frequency.
    hourly_data_df = data_15_min_df.resample('h').apply(ohlc_dict)

    hourly_data_df.dropna(subset=['open', 'high', 'low', 'close'], how='all', inplace=True)

    return hourly_data_df

def get_price_data_daily(ticker: str, start_date: datetime, end_date: datetime):
    """
    Fetches daily aggregated price data directly from the database.
    Much more efficient than fetching 15-min data and resampling.
    """
    ticker = ticker.upper()
    session = MarketSession()
    
    try:
        from sqlalchemy import text
        
        # Simple and efficient SQL query
        sql_query = text("""
        WITH daily_data AS (
            SELECT 
                DATE(p.datetime) as date,
                p.datetime,
                p.open,
                p.high,
                p.low,
                p.close,
                p.volume,
                ROW_NUMBER() OVER (PARTITION BY DATE(p.datetime) ORDER BY p.datetime ASC) as rn_first,
                ROW_NUMBER() OVER (PARTITION BY DATE(p.datetime) ORDER BY p.datetime DESC) as rn_last
            FROM price_data.prices p
            JOIN ticker_universe.tickers t ON p.ticker_id = t.id
            WHERE t.ticker = :ticker
                AND p.datetime >= :start_date
                AND p.datetime <= :end_date
        )
        SELECT 
            date,
            MAX(CASE WHEN rn_first = 1 THEN open END) as open,
            MAX(high) as high,
            MIN(low) as low,
            MAX(CASE WHEN rn_last = 1 THEN close END) as close,
            SUM(volume) as volume
        FROM daily_data
        GROUP BY date
        ORDER BY date
        """)
        
        # Execute query
        df = pd.read_sql(
            sql_query,
            session.bind,
            params={
                'ticker': ticker,
                'start_date': start_date,
                'end_date': end_date
            }
        )
        
        if df.empty:
            ticker_exists = session.query(Ticker).filter(Ticker.ticker == ticker).first()
            if not ticker_exists:
                logger.debug("Ticker '%s' not found in database", ticker)
            else:
                logger.debug("Ticker '%s' exists but no price data for date range %s to %s", ticker, start_date, end_date)
                
        return df
        
    finally:
        session.close()

def fetch_bulk_price_data_for_tickers(tickers: list, start_date_str: str, end_date_str: str, frequency: str = 'daily'):
    """
    Fetch price data for multiple tickers in parallel.
    
    Parameters:
    - tickers: List of ticker symbols
    - start_date_str: Start date in 'YYYY-MM-DD' format
    - end_date_str: End date in 'YYYY-MM-DD' format
    
    Returns:
    - dict: Mapping of ticker to price series
    """
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    if frequency == 'daily':
        get_price_data_func = get_price_data_daily
    elif frequency == '15mins':
        get_price_data_func = get_price_data_15_mins
    elif frequency == 'hourly':
        get_price_data_func = get_price_data_hourly

    price_data_map = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(get_price_data_func, ticker, start_date, end_date): ticker
            for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                if data is not None and not data.empty:
                    # Handle different data formats based on frequency
                    if frequency == 'daily':
                        # Daily data has 'date' column
                        data['date'] = pd.to_datetime(data['date'])
                        price_data_map[ticker] = data.set_index('date')['close']
                    else:
                        # 15mins and hourly data already have datetime as index
                        price_data_map[ticker] = data['close']
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                
    return price_data_map


def get_dividends_series(ticker: str, start_date: datetime, end_date: datetime) -> pd.Series:
    """Return a pandas Series of dividends for a ticker between dates.

    Index: datetime (ex-dividend date), Values: dividend amount (float)
    """
    session = MarketSession()
    try:
        # Join on ticker and filter by date
        rows = (
            session.query(Dividend)
            .join(Ticker)
            .filter(
                Ticker.ticker == ticker.upper(),
                Dividend.date >= start_date.date(),
                Dividend.date <= end_date.date(),
            )
            .order_by(Dividend.date)
            .all()
        )
        if not rows:
            return pd.Series(dtype=float)
        # Prefer adjusted dividend if available, fallback to raw
        data = {pd.to_datetime(r.date): float(r.adjDividend if r.adjDividend is not None else (r.dividend or 0.0)) for r in rows}
        return pd.Series(data).sort_index()
    finally:
        session.close()
