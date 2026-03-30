"""Earnings proximity rule — exit positions approaching an earnings date."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.rules.base import TradingRule

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class EarningsProximityRule(TradingRule):
    """Force exit when a ticker's next earnings date is within N days.

    Queries the ``Ticker.earnings_announcement`` column from the DB on
    first encounter per ticker and caches the result. If the earnings
    date falls within ``days`` of the current bar, the position is
    force-closed and new entries are blocked.

    Args:
        days: Number of days before earnings to trigger exit/block entry.
    """

    def __init__(self, days: int):
        self.days = days
        self._cache: dict[str, datetime | None] = {}

    # ================================
    # --> Helper funcs
    # ================================

    def _get_earnings_date(self, ticker: str, current_ts: datetime) -> datetime | None:
        """Fetch and cache the next earnings date for a ticker.

        Refreshes the cache if the previously cached date is in the past
        (earnings already happened, DB may have the next one).

        Args:
            ticker: Symbol to look up.
            current_ts: Current bar timestamp for staleness check.

        Returns:
            Next earnings datetime, or None if unavailable.
        """
        cached = self._cache.get(ticker)
        if cached is not None and cached > current_ts:
            return cached

        # Reason: only query DB when cache is empty or stale
        earnings_dt = self._query_earnings_date(ticker)
        self._cache[ticker] = earnings_dt
        return earnings_dt

    def _query_earnings_date(self, ticker: str) -> datetime | None:
        """Query the Ticker table for the earnings announcement date.

        Args:
            ticker: Symbol to look up.

        Returns:
            Earnings announcement datetime, or None if not found.
        """
        from prophitai_data.db.config import MarketSession
        from prophitai_data.db.models.market import Ticker

        with MarketSession() as session:
            result = session.query(Ticker.earnings_announcement).filter(
                Ticker.ticker == ticker,
            ).scalar()
        return result

    def _is_near_earnings(self, ticker: str, timestamp: datetime) -> bool:
        """Check if the current bar is within the earnings proximity window.

        Args:
            ticker: Symbol to check.
            timestamp: Current bar timestamp.

        Returns:
            True if earnings date is within ``self.days`` days of timestamp.
        """
        earnings_dt = self._get_earnings_date(ticker, timestamp)
        if earnings_dt is None:
            return False
        days_until = (earnings_dt - timestamp).total_seconds() / 86400
        return 0 <= days_until <= self.days

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        """Block new entries when earnings are within the proximity window."""
        return self._is_near_earnings(ticker, timestamp)

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        """Force exit when an open position is near its earnings date."""
        return self._is_near_earnings(ticker, timestamp)
