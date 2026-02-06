"""Commodity price data retrieval from the macro database."""

from datetime import date
from typing import Optional

from pandas import DataFrame

from app.db.core.models.macro_data_models import CommodityPrices
from app.utils.decorators.database import with_session


@with_session('macro')
def get_commodity_prices(
    symbol: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session=None
):
    """
    Fetch commodity OHLCV price data for a given symbol.

    Args:
        symbol: Commodity symbol (e.g., "GCUSD" for gold)
        start_date: Optional start date for filtering (inclusive)
        end_date: Optional end date for filtering (inclusive)
        session: Database session (injected by decorator)

    Returns:
        DataFrame with columns: symbol, date, open, high, low, close, volume
    """
    query = session.query(CommodityPrices).filter(CommodityPrices.symbol == symbol)

    # Add date filters if provided
    if start_date:
        query = query.filter(CommodityPrices.date >= start_date)
    if end_date:
        query = query.filter(CommodityPrices.date <= end_date)

    # Order by date ascending
    query = query.order_by(CommodityPrices.date.asc())

    prices = query.all()

    # Convert to DataFrame with only relevant OHLCV columns
    df = DataFrame([
        {
            'symbol': price.symbol,
            'date': price.date,
            'open': price.open,
            'high': price.high,
            'low': price.low,
            'close': price.close,
            'volume': price.volume
        }
        for price in prices
    ])

    return df
