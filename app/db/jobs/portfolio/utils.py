"""
Portfolio monitoring utilities.

This module provides functions to classify portfolio positions into asset
class buckets (equities, fixed income, commodities, etc.) based on ticker
metadata from the database, and utilities for persisting alert state.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.core.models.market_data_models import PriceTargetNews, Ticker
from app.db.core.models.user_data_models import Portfolio
from app.db.core.db_config import MarketSession
from app.db.jobs.portfolio.models import (
    DriftResult,
    DrawdownResult,
    PortfolioCorrelationResult,
)
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.time_utils import get_current_utc_time

# =============================================================================
# DEDUPLICATION THRESHOLDS
# =============================================================================
# Reason: Define material worsening thresholds to avoid alerting on minor fluctuations
DRIFT_WORSENING_THRESHOLD = 0.02      # 2% additional drift to consider "worsened"
DRAWDOWN_WORSENING_THRESHOLD = 0.05   # 5% deeper drawdown to consider "worsened"
CORRELATION_WORSENING_THRESHOLD = 0.10  # 10% increase in avg correlation
ALERT_COOLDOWN_HOURS = 168            # 7 days before re-alerting for same condition

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


# =============================================================================
# ALERT DEDUPLICATION
# =============================================================================

def _cooldown_passed(last_alerted_at: Optional[str], hours: int = ALERT_COOLDOWN_HOURS) -> bool:
    """
    Check if enough time has passed since last alert.

    Args:
        last_alerted_at: ISO timestamp of last alert, or None if never alerted.
        hours: Cooldown period in hours.

    Returns:
        True if cooldown has passed or never alerted before.
    """
    if not last_alerted_at:
        return True
    last_alert_time = datetime.fromisoformat(last_alerted_at)
    return get_current_utc_time() - last_alert_time > timedelta(hours=hours)


def should_send_drift_alert(
    current: DriftResult,
    previous_state: Optional[Dict],
) -> bool:
    """
    Determine if drift alert should be sent based on deduplication rules.

    Returns True if:
    - Current triggered AND no previous state exists
    - OR current triggered AND previous was not triggered
    - OR current triggered AND new sector entered drift territory
    - OR current triggered AND any sector drift worsened by threshold
    - OR current triggered AND cooldown period passed

    Args:
        current: Current drift detection result.
        previous_state: Previous alert state dict for drift, or None.

    Returns:
        True if alert should be sent.
    """
    if not current.triggered:
        return False

    # No previous state = new alert
    if not previous_state:
        return True

    prev_result = previous_state.get('result', {})
    prev_triggered = prev_result.get('triggered', False)

    # Previous wasn't triggered = new condition
    if not prev_triggered:
        return True

    # Check cooldown
    if _cooldown_passed(previous_state.get('last_alerted_at')):
        return True

    # Check for new sectors in drift
    current_sectors = set(current.flagged_sectors.keys())
    previous_sectors = set(prev_result.get('flagged_sectors', {}).keys())
    if current_sectors - previous_sectors:
        return True

    # Check for material worsening in any sector
    for sector, details in current.flagged_sectors.items():
        prev_sector = prev_result.get('flagged_sectors', {}).get(sector, {})
        prev_drift = abs(prev_sector.get('drift', 0))
        current_drift = abs(details.drift)
        if current_drift - prev_drift >= DRIFT_WORSENING_THRESHOLD:
            return True

    return False


def should_send_drawdown_alert(
    current: DrawdownResult,
    previous_state: Optional[Dict],
) -> bool:
    """
    Determine if drawdown alert should be sent based on deduplication rules.

    Returns True if:
    - Current triggered AND no previous state exists
    - OR current triggered AND previous was not triggered
    - OR current triggered AND new position entered drawdown
    - OR current triggered AND any position drawdown worsened by threshold
    - OR current triggered AND cooldown period passed

    Args:
        current: Current drawdown detection result.
        previous_state: Previous alert state dict for drawdown, or None.

    Returns:
        True if alert should be sent.
    """
    if not current.triggered:
        return False

    # No previous state = new alert
    if not previous_state:
        return True

    prev_result = previous_state.get('result', {})
    prev_triggered = prev_result.get('triggered', False)

    # Previous wasn't triggered = new condition
    if not prev_triggered:
        return True

    # Check cooldown
    if _cooldown_passed(previous_state.get('last_alerted_at')):
        return True

    # Check for new positions in drawdown
    current_positions = set(current.flagged_positions.keys())
    previous_positions = set(prev_result.get('flagged_positions', {}).keys())
    if current_positions - previous_positions:
        return True

    # Check for material worsening in any position
    # Reason: Drawdowns are negative, so -0.20 is worse than -0.15
    for ticker, details in current.flagged_positions.items():
        prev_position = prev_result.get('flagged_positions', {}).get(ticker, {})
        prev_drawdown = prev_position.get('current_drawdown', 0)
        # More negative = worse, so check if current is threshold more negative
        if details.current_drawdown - prev_drawdown <= -DRAWDOWN_WORSENING_THRESHOLD:
            return True

    return False


def should_send_correlation_alert(
    current: PortfolioCorrelationResult,
    previous_state: Optional[Dict],
) -> bool:
    """
    Determine if correlation alert should be sent based on deduplication rules.

    Returns True if:
    - Current triggered AND no previous state exists
    - OR current triggered AND previous was not triggered
    - OR current triggered AND recent_avg increased by threshold
    - OR current triggered AND trend changed to "Rising"
    - OR current triggered AND cooldown period passed

    Args:
        current: Current correlation detection result.
        previous_state: Previous alert state dict for correlation, or None.

    Returns:
        True if alert should be sent.
    """
    if not current.triggered:
        return False

    # No previous state = new alert
    if not previous_state:
        return True

    prev_result = previous_state.get('result', {})
    prev_triggered = prev_result.get('triggered', False)

    # Previous wasn't triggered = new condition
    if not prev_triggered:
        return True

    # Check cooldown
    if _cooldown_passed(previous_state.get('last_alerted_at')):
        return True

    # Check for material worsening in correlation
    prev_recent_avg = prev_result.get('recent_avg', 0)
    if current.recent_avg - prev_recent_avg >= CORRELATION_WORSENING_THRESHOLD:
        return True

    # Check if trend shifted to Rising (concerning direction)
    prev_trend = prev_result.get('trend', 'N/A')
    if current.trend == 'Rising' and prev_trend != 'Rising':
        return True

    return False


def save_alert_state(
    session: Session,
    portfolio_id: UUID,
    drift_result: DriftResult,
    drawdown_result: DrawdownResult,
    correlation_result: PortfolioCorrelationResult,
    sector_allocation_preferences: Optional[Dict[str, float]] = None,
    drift_alerted: bool = False,
    drawdown_alerted: bool = False,
    correlation_alerted: bool = False,
) -> None:
    """
    Save detection results to portfolio's alert_state column.

    Stores all detection results (triggered or not) with timestamps for
    deduplication logic. Each alert type tracks:
    - result: Full detection result for comparison
    - last_checked_at: When detection last ran (always updated)
    - last_alerted_at: When alert was last sent (only updated if alert was sent)

    Also stores sector allocation preferences for easy comparison with actual allocations.

    Args:
        session: SQLAlchemy session for the user database.
        portfolio_id: UUID of the portfolio to update.
        drift_result: Result from allocation drift detection.
        drawdown_result: Result from drawdown detection.
        correlation_result: Result from correlation detection.
        sector_allocation_preferences: User's target sector allocation percentages.
        drift_alerted: Whether a drift alert was actually sent this run.
        drawdown_alerted: Whether a drawdown alert was actually sent this run.
        correlation_alerted: Whether a correlation alert was actually sent this run.
    """
    now_iso = get_current_utc_time().isoformat()

    portfolio = session.query(Portfolio).filter(
        Portfolio.id == portfolio_id
    ).first()

    if not portfolio:
        return

    # Start with existing state or empty dict
    alert_state = portfolio.alert_state or {}

    # Update drift - always store result, only update last_alerted_at if alert was sent
    prev_drift_alerted = alert_state.get('drift', {}).get('last_alerted_at')
    alert_state['drift'] = {
        'result': drift_result.model_dump(),
        'sector_allocation_preferences': sector_allocation_preferences,
        'last_checked_at': now_iso,
        'last_alerted_at': now_iso if drift_alerted else prev_drift_alerted
    }

    # Update drawdown - always store result, only update last_alerted_at if alert was sent
    prev_drawdown_alerted = alert_state.get('drawdown', {}).get('last_alerted_at')
    alert_state['drawdown'] = {
        'result': drawdown_result.model_dump(),
        'last_checked_at': now_iso,
        'last_alerted_at': now_iso if drawdown_alerted else prev_drawdown_alerted
    }

    # Update correlation - always store result, only update last_alerted_at if alert was sent
    prev_correlation_alerted = alert_state.get('correlation', {}).get('last_alerted_at')
    alert_state['correlation'] = {
        'result': correlation_result.model_dump(),
        'last_checked_at': now_iso,
        'last_alerted_at': now_iso if correlation_alerted else prev_correlation_alerted
    }

    portfolio.alert_state = alert_state
    # Reason: SQLAlchemy doesn't detect in-place mutations of JSONB columns
    flag_modified(portfolio, 'alert_state')
    session.commit()

