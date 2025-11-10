from app.db.core.db_config import MacroDataSession
from app.db.core.models.macro_data_models import CommodityPrices, GovernmentBondRates
from app.utils.decorators.database import with_session
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from pandas import DataFrame
from typing import Optional


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


@with_session('macro')
def get_government_bond_rates(
    country: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session=None
):
    """
    Fetch government bond rates (yield curve) for a given country.

    Args:
        country: Country code (e.g., "ES" for Spain, "US" for United States)
        start_date: Optional start date for filtering (inclusive)
        end_date: Optional end date for filtering (inclusive)
        session: Database session (injected by decorator)

    Returns:
        DataFrame with columns: country, date, m1, m2, m3, m6, y1, y2, y3, y5, y7, y10, y20, y30
    """
    query = session.query(GovernmentBondRates).filter(GovernmentBondRates.country == country)

    # Add date filters if provided
    if start_date:
        query = query.filter(GovernmentBondRates.date >= start_date)
    if end_date:
        query = query.filter(GovernmentBondRates.date <= end_date)

    # Order by date ascending
    query = query.order_by(GovernmentBondRates.date.asc())

    rates = query.all()

    # Convert to DataFrame with only relevant columns (drop id, created_at, updated_at, _sa_instance_state)
    df = DataFrame([
        {
            'country': rate.country,
            'date': rate.date,
            'm1': rate.m1,
            'm2': rate.m2,
            'm3': rate.m3,
            'm6': rate.m6,
            'y1': rate.y1,
            'y2': rate.y2,
            'y3': rate.y3,
            'y5': rate.y5,
            'y7': rate.y7,
            'y10': rate.y10,
            'y20': rate.y20,
            'y30': rate.y30
        }
        for rate in rates
    ])

    return df

