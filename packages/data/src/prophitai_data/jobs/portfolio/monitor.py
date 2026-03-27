"""
Portfolio preference monitoring and drift detection.

This module provides functionality to monitor portfolio allocations against
user-defined preferences and detect when actual allocations have drifted
from target allocations.
"""
from datetime import datetime
from typing import Dict, Tuple
from uuid import UUID

import pandas as pd

from prophitai_data.db.config import UserSession, MarketSession
from prophitai_data.db.models.user import Portfolio, PortfolioItem, PortfolioPreference
from prophitai_data.jobs.portfolio.detections import (
    detect_allocation_drift,
    detect_drawdowns,
    detect_portfolio_correlation_change
)
from prophitai_data.jobs.portfolio.messages import send_portfolio_alert
from prophitai_data.jobs.portfolio.utils import (
    save_alert_state,
    should_send_drift_alert,
    should_send_drawdown_alert,
    should_send_correlation_alert,
)

class MonitorPortfolio:
    """
    Monitor portfolio allocations and detect drift from preferences.

    This class compares current portfolio allocations against user-defined
    target allocations to identify sectors that have drifted beyond acceptable
    thresholds.

    Usage:
        with MonitorPortfolio(portfolio_id) as monitor:
            drift_result, drawdown_result = monitor.notify()
            if drift_result['triggered']:
                print(drift_result['flagged_sectors'])
    """

    def __init__(self, portfolio_id: str, returns_df: pd.DataFrame | None = None):
        self.portfolio_id = portfolio_id
        self._returns_df = returns_df
        self._user_session: UserSession | None = None
        self._market_session: MarketSession | None = None
        self._preferences: Dict[str, float] | None = None
        self._positions: Dict[str, float] | None = None
        self._portfolio_created_date: datetime | None = None
        self._user_id: UUID | None = None
        self._portfolio_name: str | None = None
        self._previous_alert_state: Dict | None = None

    def __enter__(self) -> "MonitorPortfolio":
        self._user_session = UserSession()
        self._market_session = MarketSession()
        self._preferences, self._positions = self._get_data()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        if self._user_session:
            self._user_session.close()
        if self._market_session:
            self._market_session.close()

    @property
    def preferences(self) -> Dict[str, float]:
        if self._preferences is None:
            raise RuntimeError("MonitorPortfolio must be used as a context manager")
        return self._preferences

    @property
    def positions(self) -> Dict[str, float]:
        if self._positions is None:
            raise RuntimeError("MonitorPortfolio must be used as a context manager")
        return self._positions

    @property
    def portfolio_created_date(self) -> datetime:
        if self._portfolio_created_date is None:
            raise RuntimeError("MonitorPortfolio must be used as a context manager")
        return self._portfolio_created_date

    @property
    def market_session(self) -> MarketSession:
        if self._market_session is None:
            raise RuntimeError("MonitorPortfolio must be used as a context manager")
        return self._market_session

    @property
    def user_id(self) -> UUID:
        if self._user_id is None:
            raise RuntimeError("MonitorPortfolio must be used as a context manager")
        return self._user_id

    @property
    def portfolio_name(self) -> str:
        if self._portfolio_name is None:
            raise RuntimeError("MonitorPortfolio must be used as a context manager")
        return self._portfolio_name

    @property
    def previous_alert_state(self) -> Dict | None:
        """Previous alert state from database, or None if never monitored."""
        return self._previous_alert_state

    def _get_data(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Fetch portfolio preferences and positions from database.

        Returns:
            Tuple containing:
                - preferences: Dict mapping sector names to target allocations
                - positions: Dict mapping tickers to current allocations

        Raises:
            ValueError: If no preferences or positions found for portfolio
            RuntimeError: If called outside of context manager
        """
        if self._user_session is None:
            raise RuntimeError("_get_data must be called within context manager")

        # Reason: Fetch portfolio metadata for downstream calculations and notifications
        portfolio_row = self._user_session.query(
            Portfolio.created_date,
            Portfolio.user_id,
            Portfolio.name,
            Portfolio.alert_state,
        ).filter(
            Portfolio.id == self.portfolio_id
        ).first()
        if portfolio_row:
            self._portfolio_created_date = portfolio_row.created_date
            self._user_id = portfolio_row.user_id
            self._portfolio_name = portfolio_row.name
            self._previous_alert_state = portfolio_row.alert_state
        else:
            raise ValueError(f"No portfolio found with id {self.portfolio_id}")

        # Pull the portfolio preference from the database
        preferences_row = self._user_session.query(
            PortfolioPreference.equities_allocation,
            PortfolioPreference.fixed_income_allocation,
            PortfolioPreference.commodities_allocation,
            PortfolioPreference.currencies_allocation,
            PortfolioPreference.cryptocurrencies_allocation,
            PortfolioPreference.alternatives_hedge_funds_allocation,
            PortfolioPreference.alternatives_pe_vc_allocation,
            PortfolioPreference.cash_allocation,
        ).filter(
            PortfolioPreference.portfolio_id == self.portfolio_id
        ).first()

        if preferences_row:
            # Reason: Map database columns to bucket names that match utils.py classification
            raw_keys = [
                'equities', 'fixed_income', 'commodities', 'currencies',
                'cryptocurrencies', 'alternatives_hedge_funds', 'alternatives_pe_vc', 'cash'
            ]
            raw_prefs = {k: float(v) for k, v in zip(raw_keys, preferences_row) if v is not None}

            # Reason: Combine hedge funds and PE/VC into single 'alternatives' bucket
            alternatives_total = (
                raw_prefs.pop('alternatives_hedge_funds', 0.0) +
                raw_prefs.pop('alternatives_pe_vc', 0.0)
            )
            if alternatives_total > 0:
                raw_prefs['alternatives'] = alternatives_total

            preferences = raw_prefs
        else:
            raise ValueError(f"No preferences found for portfolio {self.portfolio_id}")

        positions_rows = self._user_session.query(
            PortfolioItem.ticker,
            PortfolioItem.allocation
        ).filter(
            PortfolioItem.portfolio_id == self.portfolio_id
        ).all()

        if positions_rows:
            positions = {p.ticker: float(p.allocation) for p in positions_rows}
        else:
            raise ValueError(f"No positions found for portfolio {self.portfolio_id}")

        return preferences, positions

    def notify(self):
        """
        Run all detections and send alerts based on deduplication rules.

        Alerts are only sent when:
        - The condition is new (no previous alert or previous wasn't triggered)
        - The condition has materially worsened
        - The cooldown period has passed (7 days)

        Returns:
            Tuple of (drift_result, drawdown_result, correlation_result)
        """
        allocation_drift_result = detect_allocation_drift(self.positions, self.preferences, self.market_session)
        drawdown_result = detect_drawdowns(self.positions, self.portfolio_created_date, returns_df=self._returns_df)
        portfolio_correlation_result = detect_portfolio_correlation_change(self.positions, returns_df=self._returns_df)

        # Determine which alerts should be sent based on deduplication rules
        prev_state = self.previous_alert_state or {}
        send_drift = should_send_drift_alert(
            allocation_drift_result,
            prev_state.get('drift')
        )
        send_drawdown = should_send_drawdown_alert(
            drawdown_result,
            prev_state.get('drawdown')
        )
        send_correlation = should_send_correlation_alert(
            portfolio_correlation_result,
            prev_state.get('correlation')
        )

        # Only send alerts that passed deduplication checks
        if any([send_drift, send_drawdown, send_correlation]):
            send_portfolio_alert(
                user_id=self.user_id,
                portfolio_id=self.portfolio_id,
                portfolio_name=self.portfolio_name,
                drift_result=allocation_drift_result if send_drift else None,
                drawdown_result=drawdown_result if send_drawdown else None,
                correlation_result=portfolio_correlation_result if send_correlation else None
            )

        # Always persist detection results, but only update last_alerted_at for sent alerts
        save_alert_state(
            session=self._user_session,
            portfolio_id=UUID(self.portfolio_id),
            drift_result=allocation_drift_result,
            drawdown_result=drawdown_result,
            correlation_result=portfolio_correlation_result,
            sector_allocation_preferences=self.preferences,
            drift_alerted=send_drift,
            drawdown_alerted=send_drawdown,
            correlation_alerted=send_correlation,
        )

        return allocation_drift_result, drawdown_result, portfolio_correlation_result
