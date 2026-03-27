from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from prophitai_data.db.models.market import *
from datetime import datetime
import logging
from prophitai_data.session import with_session
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
    Fetches daily price data for a single ticker.
    If start_date or end_date is None, queries all available data.
    """
    ticker = ticker.upper()

    query = session.query(
        DailyPrices.datetime.label('date'),
        DailyPrices.open,
        DailyPrices.high,
        DailyPrices.low,
        DailyPrices.close,
        DailyPrices.adj_close,
        DailyPrices.volume,
    ).join(Ticker).filter(Ticker.ticker == ticker)

    if start_date:
        query = query.filter(DailyPrices.datetime >= start_date)
    if end_date:
        query = query.filter(DailyPrices.datetime <= end_date)

    query = query.order_by(DailyPrices.datetime.asc())

    # Reason: pd.read_sql bypasses ORM object hydration, reading directly into a DataFrame
    return pd.read_sql(query.statement, session.bind)


@with_session('market')
def _get_bulk_daily_prices(
    tickers: list[str], start_date: datetime, end_date: datetime, session=None,
) -> dict[str, pd.DataFrame]:
    """Fetch daily OHLCV for multiple tickers in a single query.

    Args:
        tickers: List of ticker symbols.
        start_date: Start datetime for the range.
        end_date: End datetime for the range.
        session: Database session (injected by decorator).

    Returns:
        Dict mapping ticker -> DataFrame with DatetimeIndex and columns
        [open, high, low, close, adj_close, volume].
    """
    tickers_upper = [t.upper() for t in tickers]

    query = (
        session.query(
            Ticker.ticker,
            DailyPrices.datetime.label('date'),
            DailyPrices.open,
            DailyPrices.high,
            DailyPrices.low,
            DailyPrices.close,
            DailyPrices.adj_close,
            DailyPrices.volume,
        )
        .join(Ticker, DailyPrices.ticker_id == Ticker.id)
        .filter(
            Ticker.ticker.in_(tickers_upper),
            DailyPrices.datetime >= start_date,
            DailyPrices.datetime <= end_date,
        )
        .order_by(Ticker.ticker, DailyPrices.datetime.asc())
    )

    # Reason: use session.connection() to reuse the session's existing connection
    # instead of session.bind which checks out a second connection from the pool
    df = pd.read_sql(query.statement, session.connection())

    if df.empty:
        return {}

    df['date'] = pd.to_datetime(df['date'])
    result: dict[str, pd.DataFrame] = {}
    for ticker, group in df.groupby('ticker'):
        result[str(ticker)] = group.drop(columns=['ticker']).set_index('date')

    return result


def _fetch_bulk_threaded(tickers: list, start_date: datetime, end_date: datetime, frequency: str) -> dict[str, pd.DataFrame]:
    """Fetch price data for multiple tickers.

    For daily frequency, uses a single bulk SQL query. For intraday
    frequencies (15mins, hourly), uses a thread pool for parallel fetching.
    """
    # Reason: daily is the hot path (universe of 52 tickers); single query is 10-50x faster
    if frequency == 'daily':
        return _get_bulk_daily_prices(tickers, start_date, end_date)

    func_map = {
        '15mins': get_price_data_15_mins,
        'hourly': get_price_data_hourly,
    }
    get_func = func_map[frequency]

    price_data_map: dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {
            executor.submit(get_func, ticker, start_date, end_date): ticker
            for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                if data is not None and not data.empty:
                    price_data_map[ticker] = data
            except Exception as e:
                logger.error("Error fetching %s data for %s: %s", frequency, ticker, e)

    return price_data_map


def fetch_bulk_price_data_for_tickers(tickers: list, start_date_str: str, end_date_str: str, frequency: str = 'daily') -> pd.DataFrame:
    """
    Fetch price data for multiple tickers.

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
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    if frequency not in ('daily', '15mins', 'hourly'):
        raise ValueError(f"Invalid frequency: {frequency}. Must be 'daily', '15mins', or 'hourly'")

    bulk_data = _fetch_bulk_threaded(tickers, start_date, end_date, frequency)

    # Reason: adj_close accounts for dividends and splits
    price_col = 'adj_close' if frequency == 'daily' else 'close'
    price_data_map = {ticker: df[price_col] for ticker, df in bulk_data.items()}

    return pd.DataFrame(price_data_map)

def fetch_bulk_ohlcv_data_for_tickers(tickers: list, start_date_str: str, end_date_str: str, frequency: str = 'daily'):
    """
    Fetch full OHLCV DataFrames for multiple tickers.

    Unlike fetch_bulk_price_data_for_tickers which returns only close Series,
    this function returns complete DataFrames with all price columns.

    Parameters:
    - tickers: List of ticker symbols
    - start_date_str: Start date in 'YYYY-MM-DD' format
    - end_date_str: End date in 'YYYY-MM-DD' format
    - frequency: Data frequency - 'daily', '15mins', or 'hourly'

    Returns:
    - dict: Mapping of ticker to DataFrame with columns [open, high, low, close, adj_close, volume]
            Index is DatetimeIndex

    Example:
        >>> data = fetch_bulk_ohlcv_data_for_tickers(['AAPL', 'SPY'], '2024-01-01', '2024-12-31')
        >>> data['AAPL']  # Returns full DataFrame with OHLCV columns
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    if frequency not in ('daily', '15mins', 'hourly'):
        raise ValueError(f"Invalid frequency: {frequency}. Must be 'daily', '15mins', or 'hourly'")

    # Reason: check process-level cache for already-fetched OHLCV data (daily only — intraday not used by agent tools)
    from prophitai_data.cache import get_cache
    cache = get_cache()

    if frequency == 'daily':
        cached, missing = cache.get_ohlcv(tickers, start_date_str, end_date_str)
        if not missing:
            price_data_map = cached
        else:
            fetched = _fetch_bulk_threaded(missing, start_date, end_date, frequency)
            cache.put_ohlcv(fetched)
            price_data_map = {**cached, **fetched}
    else:
        price_data_map = _fetch_bulk_threaded(tickers, start_date, end_date, frequency)

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
    )

    returns_series = {ticker: data['adj_close'].pct_change(fill_method=None) for ticker, data in price_data.items()}
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
