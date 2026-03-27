"""Screener data access — query pre-computed EquityScreener and ETFScreener tables."""

from typing import Dict, List

import pandas as pd

from prophitai_data.db.models.market import EquityScreener, ETFScreener, Ticker
from prophitai_data.db.utils import serialize_sqlalchemy_obj
from prophitai_data.session import with_session


@with_session('market')
def get_equity_screener(tickers: List[str], session=None) -> List[Dict]:
    """Fetch equity screener data for the given tickers.

    Returns:
        List of dicts with all screener columns for each matched ticker.
    """
    rows = (
        session.query(EquityScreener)
        .join(Ticker, EquityScreener.ticker_id == Ticker.id)
        .filter(Ticker.ticker.in_(tickers))
        .all()
    )
    return [serialize_sqlalchemy_obj(row) for row in rows]


@with_session('market')
def get_etf_screener(tickers: List[str], session=None) -> List[Dict]:
    """Fetch ETF screener data for the given tickers.

    Returns:
        List of dicts with all screener columns for each matched ticker.
    """
    rows = (
        session.query(ETFScreener)
        .join(Ticker, ETFScreener.ticker_id == Ticker.id)
        .filter(Ticker.ticker.in_(tickers))
        .all()
    )
    return [serialize_sqlalchemy_obj(row) for row in rows]


@with_session('market')
def get_full_equity_universe(session=None) -> pd.DataFrame:
    """Return the entire equity screener table as a DataFrame."""
    rows = session.query(EquityScreener).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([serialize_sqlalchemy_obj(r) for r in rows])


@with_session('market')
def get_full_etf_universe(session=None) -> pd.DataFrame:
    """Return the entire ETF screener table as a DataFrame."""
    rows = session.query(ETFScreener).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([serialize_sqlalchemy_obj(r) for r in rows])
