"""
Portfolio classification utilities.

This module provides functions to classify portfolio positions into asset
class buckets (equities, fixed income, commodities, etc.) based on ticker
metadata from the database.
"""
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db.core.models.market_data_models import Ticker

# Reason: Maps industry values to bucket names for DRY classification logic
INDUSTRY_TO_BUCKET = {
    'equity_etfs': 'equities',
    'fixed_income_etfs': 'fixed_income',
    'commodity_etfs': 'commodities',
    'cryptocurrency_etfs': 'cryptocurrencies',
    'alternative_etfs': 'alternatives',
    'currency_etfs': 'currencies',
}

# Reason: All possible allocation buckets for consistent return structure
ALL_BUCKETS = [
    'equities', 'fixed_income', 'commodities', 'cryptocurrencies',
    'alternatives', 'currencies', 'cash'
]

def classify_and_add_tickers(positions: Dict[str, float], session: Session) -> Dict[str, float]:
    """
    Classify tickers into asset class buckets and sum allocations.

    Takes a dictionary of ticker positions and classifies each ticker into
    the appropriate asset class bucket based on its sector/industry metadata.

    Args:
        positions: Dict mapping ticker symbols to their allocation percentages.
        session: SQLAlchemy session for querying ticker metadata.

    Returns:
        Dict mapping bucket names to total allocation percentages.
        Always includes all buckets with 0.0 for empty ones.

    Example:
        >>> positions = {'AAPL': 0.25, 'SPY': 0.30, 'TLT': 0.20}
        >>> classify_and_add_tickers(positions, session)
        {'equities': 0.55, 'fixed_income': 0.20, 'commodities': 0.0, ...}
    """
    buckets: Dict[str, Dict[str, float]] = {bucket: {} for bucket in ALL_BUCKETS}

    ticker_objs = session.query(Ticker).filter(Ticker.ticker.in_(positions.keys())).all()
    ticker_map = {t.ticker: (t.sector, t.industry) for t in ticker_objs}

    for ticker, allocation in positions.items():
        sector, industry = ticker_map.get(ticker, (None, None))

        if sector and sector.startswith('equity_sector_'):
            buckets['equities'][ticker] = allocation
        elif industry in INDUSTRY_TO_BUCKET:
            bucket_name = INDUSTRY_TO_BUCKET[industry]
            buckets[bucket_name][ticker] = allocation

    # Reason: Sum allocations per bucket, always returning all buckets for consistency
    allocations = {bucket: sum(tickers.values()) for bucket, tickers in buckets.items()}

    return allocations
