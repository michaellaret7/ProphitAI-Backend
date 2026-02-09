from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from app.db.core.models.market_data_models import *
from datetime import datetime
import logging
from app.utils.decorators.database import with_session
from sqlalchemy import extract

logger = logging.getLogger(__name__)

@with_session('market')
def get_price_data_15_mins(ticker: str, start_date: datetime, end_date: datetime, session=None):
    ticker = ticker.upper()

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

@with_session('market')
def get_price_data_daily(ticker: str, start_date: datetime = None, end_date: datetime = None, session=None):
    """
    Fetches daily aggregated price data directly from the database.
    Much more efficient than fetching 15-min data and resampling.
    If start_date or end_date is None, queries all available data.
    """
    ticker = ticker.upper()
    
    # Base query
    query = session.query(DailyPrices).join(Ticker).filter(Ticker.ticker == ticker)

    # Apply date filters if provided
    if start_date:
        query = query.filter(DailyPrices.datetime >= start_date)
    if end_date:
        query = query.filter(DailyPrices.datetime <= end_date)

    query = query.order_by(DailyPrices.datetime.asc())  # Sort by date ascending

    rows = query.all()

    # Convert to DataFrame to match expected return type
    data = [
        {
            'date': row.datetime,
            'open': row.open,
            'high': row.high,
            'low': row.low,
            'close': row.close,
            'adj_close': row.adj_close,
            'volume': row.volume
        }
        for row in rows
    ]

    df = pd.DataFrame(data)

    if not df.empty:
        pass # Optional: set as index if needed

    return df

def fetch_bulk_price_data_for_tickers(tickers: list, start_date_str: str, end_date_str: str, frequency: str = 'daily') -> pd.DataFrame:
    """
    Fetch price data for multiple tickers in parallel.

    Parameters:
    - tickers: List of ticker symbols
    - start_date_str: Start date in 'YYYY-MM-DD' format
    - end_date_str: End date in 'YYYY-MM-DD' format
    - frequency: Data frequency - 'daily', '15mins', or 'hourly'

    Returns:
    - pd.DataFrame: DataFrame with DatetimeIndex and ticker columns containing prices
                    (adj_close for daily, close for intraday)

    Note: Daily data returns adj_close which accounts for dividends and splits.
    Use daily_price_returns on this data to get total returns.
    """
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    # Set end_date to end of day (23:59:59) to include all data on the end date
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    if frequency == 'daily':
        get_price_data_func = get_price_data_daily
    elif frequency == '15mins':
        get_price_data_func = get_price_data_15_mins
    elif frequency == 'hourly':
        get_price_data_func = get_price_data_hourly
    else:
        raise ValueError(f"Invalid frequency: {frequency}. Must be 'daily', '15mins', or 'hourly'")

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
                        # Daily data has 'date' column - use adj_close for total returns
                        # Reason: adj_close accounts for dividends and splits
                        data['date'] = pd.to_datetime(data['date'])
                        price_col = 'adj_close' if 'adj_close' in data.columns else 'close'
                        price_data_map[ticker] = data.set_index('date')[price_col]
                    else:
                        # 15mins and hourly data already have datetime as index
                        price_data_map[ticker] = data['close']
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")

    return pd.DataFrame(price_data_map)

def fetch_bulk_ohlcv_data_for_tickers(tickers: list, start_date_str: str, end_date_str: str, frequency: str = 'daily', returns: bool = False):
    """
    Fetch full OHLCV DataFrames for multiple tickers in parallel.

    Unlike fetch_bulk_price_data_for_tickers which returns only close Series,
    this function returns complete DataFrames with all price columns (open, high, low, close, volume).
    Use this for risk calculations that need full price data.

    Parameters:
    - tickers: List of ticker symbols
    - start_date_str: Start date in 'YYYY-MM-DD' format
    - end_date_str: End date in 'YYYY-MM-DD' format
    - frequency: Data frequency - 'daily', '15mins', or 'hourly'

    Returns:
    - dict: Mapping of ticker to DataFrame with columns [open, high, low, close, volume]
            Index is date/datetime (DatetimeIndex)

    Example:
        >>> data = fetch_bulk_ohlcv_data_for_tickers(['AAPL', 'SPY'], '2024-01-01', '2024-12-31')
        >>> data['AAPL']  # Returns full DataFrame with OHLCV columns
        >>> data_15m = fetch_bulk_ohlcv_data_for_tickers(['AAPL'], '2024-01-01', '2024-01-05', frequency='15mins')
    """
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    # Set end_date to end of day (23:59:59) to include all data on the end date
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    # Select appropriate data fetch function based on frequency
    if frequency == 'daily':
        get_price_data_func = get_price_data_daily
    elif frequency == '15mins':
        get_price_data_func = get_price_data_15_mins
    elif frequency == 'hourly':
        get_price_data_func = get_price_data_hourly
    else:
        raise ValueError(f"Invalid frequency: {frequency}. Must be 'daily', '15mins', or 'hourly'")

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
                    if frequency == 'daily':
                        # Daily data has 'date' column that needs to be set as index
                        data['date'] = pd.to_datetime(data['date'])
                        df = data.set_index('date')
                    else:
                        # 15mins and hourly data already have datetime as index
                        df = data
                    
                    # --- NEW LOGIC START ---
                    if returns:
                        # Calculate cumulative returns based on adj_close if available, else close
                        target_col = 'adj_close'

                        if target_col in df.columns:
                            # 1. Calculate simple daily returns
                            total_returns = df[target_col].pct_change()
                            price_returns = df['close'].pct_change()

                            df['returns'] = total_returns
                            df['price_returns'] = price_returns
                            
                            # 2. Calculate cumulative returns: (1 + r).cumprod() - 1
                            # This shows total return % (e.g., 0.10 for 10% total gain)
                            df['cum_total_returns'] = (1 + total_returns).cumprod() - 1
                            df['cum_price_returns'] = (1 + price_returns).cumprod() - 1
                    # --- NEW LOGIC END ---

                    price_data_map[ticker] = df
                    
            except Exception as e:
                logger.error(f"Error fetching OHLCV data for {ticker}: {e}")

    return price_data_map

def build_returns_df(
    tickers: list[str],
    start_date: str,
    end_date: str,
    frequency: str = 'daily',
    drop_na: bool = True
) -> pd.DataFrame:
    """
    Build a returns DataFrame for multiple tickers.

    Args:
        tickers: List of ticker symbols.
        start_date: Start date in 'YYYY-MM-DD' format.
        end_date: End date in 'YYYY-MM-DD' format.
        frequency: Data frequency - 'daily', '15mins', or 'hourly'.
        drop_na: If True, drop rows with any NaN across all columns.
            Set to False when building a shared cache for multiple portfolios,
            since each consumer will filter to its own tickers and handle NaN.

    Returns:
        DataFrame with DatetimeIndex and ticker columns containing returns.
    """

    price_data = fetch_bulk_ohlcv_data_for_tickers(
        tickers,
        start_date,
        end_date,
        frequency,
        returns=True
    )

    returns_series = {ticker: data['returns'] for ticker, data in price_data.items()}
    returns_df = pd.concat(returns_series, axis=1)

    returns_df.index = pd.to_datetime(returns_df.index)
    returns_df.sort_index(inplace=True)
    if drop_na:
        returns_df.dropna(inplace=True)

    return returns_df


@with_session('market')
def get_ticker_metadata(tickers: list[str], session=None) -> dict[str, tuple[str | None, str | None]]:
    """
    Fetch sector and industry metadata for given tickers.

    Args:
        tickers: List of ticker symbols to fetch metadata for.

    Returns:
        Dict mapping ticker symbol to (sector, industry) tuple.
        Tickers not found in database are excluded from result.
    """
    if not tickers:
        return {}

    ticker_objs = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
    return {t.ticker: (t.sector, t.industry) for t in ticker_objs}


if __name__ == "__main__":
    returns_df = build_returns_df(tickers=['AAPL', 'SPY'], start_date='2024-01-01', end_date='2024-12-31', frequency='daily')
    print(returns_df)

