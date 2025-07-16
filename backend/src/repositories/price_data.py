import pandas as pd
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import *
from datetime import datetime
from pandas import DataFrame

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
            print(f"Ticker '{ticker}' not found in database")
        else:
            print(f"Ticker '{ticker}' exists but no price data for date range {start_date} to {end_date}")
    
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

    # The resample might create rows for hours with no data (e.g. overnight).
    # We can remove rows where all OHLCV data is NaN.
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
                print(f"Ticker '{ticker}' not found in database")
            else:
                print(f"Ticker '{ticker}' exists but no price data for date range {start_date} to {end_date}")
                
        return df
        
    finally:
        session.close()



