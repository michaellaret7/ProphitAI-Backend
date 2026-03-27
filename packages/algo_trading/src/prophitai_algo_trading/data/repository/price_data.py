"""Price data repository — fetches OHLCV data from DB or FMP API."""

from datetime import datetime
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

    # Reason: FMP API intervals are fetched directly; DB intervals use the mapping
    if interval_enum in (Interval.FIVE_MIN, Interval.ONE_MIN):
        fmp_client = FmpClient()
        results = fmp_client.get_intraday_prices_for_ticker(symbol, start_date, end_date, interval_enum.value)
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
