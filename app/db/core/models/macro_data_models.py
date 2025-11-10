"""
Macro Data Models for macro_data database

Contains models for:
- Government bond rates (treasury yields)
- Economic indicators
- Central bank data
- Commodities price data (OHLCV)
"""
from dataclasses import dataclass
from datetime import datetime, date
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.core.db_config import MacroDataBase


# =============================================================================
# GOVERNMENT BOND RATES (PUBLIC SCHEMA)
# =============================================================================

@dataclass
class GovernmentBondRates(MacroDataBase):
    """
    Government bond rates (treasury yields) for various countries.

    Data includes yield curves and various maturities.
    Column names follow format: {number}{period} where period is 'm' (months) or 'y' (years)
    Example: 1m = 1 month, 3m = 3 months, 1y = 1 year, 10y = 10 years

    Note: Each country has a single UUID. All rows for a country share the same id (country identifier).
    Primary key is composite: (id, date)
    """
    __tablename__ = 'gov_bond_rates'
    __table_args__ = (
        UniqueConstraint('country', 'date', name='uq_country_date'),
    )

    # Composite primary key: (id, date)
    # id represents the country (same UUID for all rows of a country)
    id: Mapped[UUID] = mapped_column(primary_key=True)

    # Country and date
    country: Mapped[str] = mapped_column(String, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False, index=True)

    # Treasury maturities - months
    m1: Mapped[Optional[float]] = mapped_column(Float, name='1m', default=None)
    m2: Mapped[Optional[float]] = mapped_column(Float, name='2m', default=None)
    m3: Mapped[Optional[float]] = mapped_column(Float, name='3m', default=None)
    m6: Mapped[Optional[float]] = mapped_column(Float, name='6m', default=None)

    # Treasury maturities - years
    y1: Mapped[Optional[float]] = mapped_column(Float, name='1y', default=None)
    y2: Mapped[Optional[float]] = mapped_column(Float, name='2y', default=None)
    y3: Mapped[Optional[float]] = mapped_column(Float, name='3y', default=None)
    y5: Mapped[Optional[float]] = mapped_column(Float, name='5y', default=None)
    y7: Mapped[Optional[float]] = mapped_column(Float, name='7y', default=None)
    y10: Mapped[Optional[float]] = mapped_column(Float, name='10y', default=None)
    y20: Mapped[Optional[float]] = mapped_column(Float, name='20y', default=None)
    y30: Mapped[Optional[float]] = mapped_column(Float, name='30y', default=None)

    # Metadata (UTC timestamps)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)


# =============================================================================
# COMMODITY PRICES (PUBLIC SCHEMA)
# =============================================================================

@dataclass
class CommodityPrices(MacroDataBase):
    """
    Commodity OHLCV price data.

    Stores historical price data for commodities including:
    - Open, High, Low, Close prices
    - Volume

    Note: Each symbol has a single UUID. All rows for a symbol share the same id (symbol identifier).
    Primary key is composite: (id, date)
    """
    __tablename__ = 'commodity_prices'
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uq_commodity_symbol_date'),
    )

    # Composite primary key: (id, date)
    # id represents the symbol (same UUID for all rows of a symbol)
    id: Mapped[UUID] = mapped_column(primary_key=True)

    # Commodity identifier and date
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False, index=True)

    # OHLCV data
    open: Mapped[Optional[float]] = mapped_column(Float, default=None)
    high: Mapped[Optional[float]] = mapped_column(Float, default=None)
    low: Mapped[Optional[float]] = mapped_column(Float, default=None)
    close: Mapped[Optional[float]] = mapped_column(Float, default=None)
    volume: Mapped[Optional[float]] = mapped_column(Float, default=None)

    # Metadata (UTC timestamps)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)