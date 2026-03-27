"""Portfolio alert state query operations."""

import uuid
from typing import Optional, Dict

from prophitai_data.db.config import UserSession
from prophitai_data.db.models.user import *
from prophitai_data.session import with_session


@with_session('user')
def get_portfolio_alert_state(portfolio_id: uuid.UUID, session=None) -> Optional[Dict]:
    """
    Get portfolio alert state for risk monitoring deduplication.

    Args:
        portfolio_id: Portfolio UUID

    Returns:
        Dictionary containing alert state with drift, drawdown, and correlation
        detection results, or None if not found or no alert state exists.
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    portfolio = session.query(Portfolio).filter(
        Portfolio.id == portfolio_id
    ).first()

    if not portfolio:
        return None

    if not portfolio.alert_state:
        return {
            'portfolio_id': str(portfolio_id),
            'alert_state': None,
            'message': 'No alert state recorded yet'
        }

    return {
        'portfolio_id': str(portfolio_id),
        'alert_state': portfolio.alert_state
    }
