"""
Portfolio classification utilities.

This module provides functions to classify portfolio positions into asset
class buckets (equities, fixed income, commodities, etc.) based on ticker
metadata from the database.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.core.models.market_data_models import PriceTargetNews, Ticker
from app.db.core.db_config import MarketSession
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.time_utils import get_current_utc_time

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

def get_price_targets_around_inception(
    session: Session,
    tickers: List[str],
    inception_date: datetime,
    count_per_side: int = 3
) -> List[PriceTargetNews]:
    """
    Get price targets before and after portfolio inception date per ticker.

    Retrieves the N most recent price targets before inception and N earliest
    after inception for each ticker, providing context around the portfolio start.

    Args:
        session: SQLAlchemy session for querying.
        tickers: List of ticker symbols to fetch price targets for.
        inception_date: Portfolio inception date to split before/after.
        count_per_side: Number of price targets to fetch before and after inception.

    Returns:
        List of PriceTargetNews objects sorted by ticker and date.
    """
    if not tickers:
        return []

    ticker_ids_subq = (
        session.query(Ticker.id)
        .filter(Ticker.ticker.in_(tickers))
        .scalar_subquery()
    )

    # Reason: Get N most recent BEFORE inception (closest to inception first)
    before_subq = (
        session.query(
            PriceTargetNews.ticker_id,
            PriceTargetNews.newsURL,
            func.row_number().over(
                partition_by=PriceTargetNews.ticker_id,
                order_by=PriceTargetNews.publishedDate.desc()
            ).label('rn')
        )
        .filter(
            PriceTargetNews.ticker_id.in_(ticker_ids_subq),
            PriceTargetNews.publishedDate < inception_date
        )
        .subquery()
    )

    before_targets = (
        session.query(PriceTargetNews)
        .join(
            before_subq,
            (PriceTargetNews.ticker_id == before_subq.c.ticker_id) &
            (PriceTargetNews.newsURL == before_subq.c.newsURL)
        )
        .filter(before_subq.c.rn <= count_per_side)
        .all()
    )

    # Reason: Get N earliest AFTER inception (closest to inception first)
    after_subq = (
        session.query(
            PriceTargetNews.ticker_id,
            PriceTargetNews.newsURL,
            func.row_number().over(
                partition_by=PriceTargetNews.ticker_id,
                order_by=PriceTargetNews.publishedDate.asc()
            ).label('rn')
        )
        .filter(
            PriceTargetNews.ticker_id.in_(ticker_ids_subq),
            PriceTargetNews.publishedDate >= inception_date
        )
        .subquery()
    )

    after_targets = (
        session.query(PriceTargetNews)
        .join(
            after_subq,
            (PriceTargetNews.ticker_id == after_subq.c.ticker_id) &
            (PriceTargetNews.newsURL == after_subq.c.newsURL)
        )
        .filter(after_subq.c.rn <= count_per_side)
        .all()
    )

    # Reason: Combine and sort by ticker symbol then date for consistent ordering
    all_targets = before_targets + after_targets
    all_targets.sort(key=lambda x: (x.ticker.ticker, x.publishedDate))

    return all_targets

def get_median_price_targets(
    session: Session,
    tickers: List[str],
    count_per_side: int = 3
) -> Dict[str, float]:
    """
    Get median price target per ticker from the past year.

    Fetches price targets from 1 year ago to today, then calculates
    the median adjusted price target for each ticker.

    Args:
        session: SQLAlchemy session for querying.
        tickers: List of ticker symbols to fetch price targets for.
        count_per_side: Number of price targets to fetch before and after the midpoint.

    Returns:
        Dict mapping ticker symbol to median adjusted price target.
        Tickers with no price targets are excluded from the result.
    """
    one_year_ago = get_current_utc_time() - timedelta(days=365)
    all_targets = get_price_targets_around_inception(
        session, tickers, one_year_ago, count_per_side
    )

    # Reason: Group price targets by ticker symbol for median calculation
    targets_by_ticker: Dict[str, List[float]] = defaultdict(list)
    for target in all_targets:
        if target.adjPriceTarget is not None:
            targets_by_ticker[target.ticker.ticker].append(target.adjPriceTarget)

    # Reason: Calculate median for each ticker, excluding those with no valid targets
    return {
        ticker: median(prices)
        for ticker, prices in targets_by_ticker.items()
        if prices
    }

