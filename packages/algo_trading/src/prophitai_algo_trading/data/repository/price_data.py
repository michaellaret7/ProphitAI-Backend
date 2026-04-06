"""Price data repository — fetches OHLCV data from DB or FMP API."""

from datetime import datetime, timedelta
from enum import Enum

import pandas as pd
from pydantic import BaseModel

from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import Price, Ticker, DailyPrices
from prophitai_algo_trading.data.clients.fmp import FmpClient


# ================================
# --> Helper funcs
# ================================

OHLCV_AGG = {
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum',
}

# Reason: maps DB-sourced intervals to (model, resample_rule) to eliminate repeated if/elif
_DB_INTERVAL_MAP = {
    'DAILY':      (DailyPrices, None),
    'HOURLY':     (Price, '1h'),
    'THIRTY_MIN': (Price, '30min'),
    'FIFTEEN_MIN': (Price, None),
}


def _query_db_prices(session, model, symbol: str, start_date: datetime, end_date: datetime):
    """Build a standard price query against the given model."""
    return (
        session.query(model)
        .join(Ticker)
        .filter(
            Ticker.ticker == symbol,
            model.datetime >= start_date,
            model.datetime <= end_date,
        )
        .order_by(model.datetime.desc())
    )


class PriceData(BaseModel):
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _fetch_intraday_by_day(
    fmp_client: FmpClient,
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    interval: str,
) -> list[PriceData]:
    """Fetch intraday bars day-by-day to work around FMP's single-day limit.

    FMP's 1-min and 5-min endpoints only return data for one trading day per
    request, even when a multi-day range is provided. This helper iterates
    each calendar day, skips weekends, and collects all bars into a flat list.

    Args:
        fmp_client: Initialized FMP API client.
        symbol: Ticker symbol.
        start_date: Start of date range.
        end_date: End of date range.
        interval: FMP interval string ('1min' or '5min').

    Returns:
        Flat list of PriceData across all trading days in the range.
    """
    data: list[PriceData] = []
    current = start_date

    while current <= end_date:
        # Reason: Skip Saturday (5) and Sunday (6) to avoid wasted API calls.
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        results = fmp_client.get_intraday_prices_for_ticker(symbol, current, current, interval)

        if results:
            for item in results:
                data.append(PriceData(
                    datetime=item.get('date'),
                    open=item.get('open'),
                    high=item.get('high'),
                    low=item.get('low'),
                    close=item.get('close'),
                    volume=item.get('volume'),
                ))

        current += timedelta(days=1)

    return data


class Interval(Enum):
    DAILY = 'daily'
    HOURLY = 'hourly'
    THIRTY_MIN = '30min'
    FIFTEEN_MIN = '15min'
    FIVE_MIN = '5min'
    ONE_MIN = '1min'

    @classmethod
    def from_string(cls, value: str) -> 'Interval':
        """Convert string to Interval enum, raising ValueError if invalid."""
        for member in cls:
            if member.value == value:
                return member
        valid_intervals = [m.value for m in cls]
        raise ValueError(f"Invalid interval '{value}'. Must be one of: {valid_intervals}")


def get_price_data_df(symbol: str, start_date: datetime, end_date: datetime, interval: str = 'daily') -> pd.DataFrame:
    """Fetch OHLCV price data as a DataFrame.

    Args:
        symbol: Ticker symbol.
        start_date: Start of date range.
        end_date: End of date range.
        interval: One of 'daily', 'hourly', '30min', '15min', '5min', '1min'.

    Returns:
        DataFrame indexed by datetime with OHLCV columns.
    """
    interval_enum = Interval.from_string(interval)
    data = []
    resample_rule = None

    # Reason: FMP 1-min/5-min endpoints only return one trading day per request,
    # so we paginate day-by-day to get the full date range.
    if interval_enum in (Interval.FIVE_MIN, Interval.ONE_MIN):
        fmp_client = FmpClient()
        data = _fetch_intraday_by_day(fmp_client, symbol, start_date, end_date, interval_enum.value)
    else:
        db_config = _DB_INTERVAL_MAP.get(interval_enum.name)
        if db_config:
            model, resample_rule = db_config
            with MarketSession() as session:
                query = _query_db_prices(session, model, symbol, start_date, end_date)
                for item in query:
                    data.append(PriceData(
                        datetime=item.datetime,
                        open=item.open,
                        high=item.high,
                        low=item.low,
                        close=item.close,
                        volume=item.volume,
                    ))

    df = pd.DataFrame([d.model_dump() for d in data])

    if not df.empty:
        df = df.set_index('datetime')
        df = df.sort_index()

        if resample_rule:
            df = df.resample(resample_rule).agg(OHLCV_AGG).dropna()

    return df
