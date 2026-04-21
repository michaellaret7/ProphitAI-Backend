"""Ticker query utilities — eligibility filtering, price lookup, and sector ETF mapping.

Consolidated from app/utils/ticker_utils.py (DB-dependent functions only).
NOTE: name_to_ticker() is NOT here — it uses OpenAI and belongs in prophitai-tools.
"""

from datetime import datetime
from typing import List, Optional

from prophitai_data.db.models.market import Ticker
from prophitai_data.db.utils import serialize_sqlalchemy_obj
from prophitai_data.session import with_session


# ================================
# --> Helper funcs
# ================================

SECTOR_ETF_MAP = {
    'equity_sector_information_technology': 'XLK',
    'equity_sector_financials': 'XLF',
    'equity_sector_health_care': 'XLV',
    'equity_sector_consumer_discretionary': 'XLY',
    'equity_sector_communication_services': 'XLC',
    'equity_sector_industrials': 'XLI',
    'equity_sector_consumer_staples': 'XLP',
    'equity_sector_energy': 'XLE',
    'equity_sector_utilities': 'XLU',
    'equity_sector_real_estate': 'XLRE',
    'equity_sector_materials': 'XLB',
}

# Reason: the DB stores sectors as enum keys (e.g. 'equity_sector_industrials'),
# but downstream consumers (strategy indicators, prompts, UI) speak human-readable
# GICS labels. Keep this mapping in one place so every consumer normalizes the
# same way.
SECTOR_ENUM_TO_GICS_LABEL = {
    'equity_sector_information_technology': 'Information Technology',
    'equity_sector_financials': 'Financials',
    'equity_sector_health_care': 'Health Care',
    'equity_sector_consumer_discretionary': 'Consumer Discretionary',
    'equity_sector_communication_services': 'Communication Services',
    'equity_sector_industrials': 'Industrials',
    'equity_sector_consumer_staples': 'Consumer Staples',
    'equity_sector_energy': 'Energy',
    'equity_sector_utilities': 'Utilities',
    'equity_sector_real_estate': 'Real Estate',
    'equity_sector_materials': 'Materials',
}


def get_sector_etf(sector: str) -> Optional[str]:
    """Map a sector preference key to its corresponding sector ETF ticker."""
    return SECTOR_ETF_MAP.get(sector)


def get_gics_sector_label(sector: str) -> str:
    """Map a DB sector enum key to its human-readable GICS label.

    Unknown or empty inputs pass through unchanged so callers can distinguish
    "not in database" from a mapping miss.
    """
    if not sector:
        return sector
    return SECTOR_ENUM_TO_GICS_LABEL.get(sector, sector)


@with_session('market')
def get_most_recent_price(ticker: str, session=None) -> float:
    """Get the most recent close price for a ticker."""
    ticker = ticker.upper()
    row = session.query(Ticker).filter(Ticker.ticker == ticker).first()
    return row.price


@with_session('market')
def get_eligible_tickers(
    industry: str,
    market_cap: int,
    price: Optional[int] = None,
    dollar_volume: Optional[int] = None,
    session=None,
) -> List[str]:
    """Filter tickers by industry, market cap, and optional price/volume thresholds."""
    query = session.query(Ticker).filter(
        Ticker.industry == industry,
        Ticker.market_cap > market_cap,
    )

    if price is not None:
        query = query.filter(Ticker.price > price)

    if dollar_volume is not None:
        query = query.filter(Ticker.dollar_volume > dollar_volume)

    tickers = query.all()
    return [serialize_sqlalchemy_obj(t)['ticker'] for t in tickers]


@with_session('market')
def get_earnings_announcement(
    ticker: str,
    session=None,
) -> datetime | None:
    """Return the next stored earnings announcement timestamp for a ticker."""
    return session.query(Ticker.earnings_announcement).filter(
        Ticker.ticker == ticker,
    ).scalar()
