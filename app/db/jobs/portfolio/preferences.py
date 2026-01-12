"""
Portfolio preference monitoring and drift detection.

This module provides functionality to monitor portfolio allocations against
user-defined preferences and detect when actual allocations have drifted
from target allocations.
"""
from datetime import datetime
from typing import Dict, Tuple

from app.db.core.db_config import UserSession, MarketSession
from app.db.core.models.user_data_models import Portfolio, PortfolioItem, PortfolioPreference
from app.db.jobs.portfolio.detections import detect_allocation_drift, detect_drawdowns, detect_portfolio_correlation_change, detect_pair_correlation_changes
from app.db.jobs.portfolio.utils import classify_and_add_tickers
from app.repositories.price_data import fetch_bulk_price_data_for_tickers, fetch_bulk_ohlcv_data_for_tickers
from app.repositories.messaging_data import (
    create_conversation,
    get_conversation,
    get_conversation_by_users,
    get_or_create_conversation,
    get_user_conversations,
    create_message,
    get_messages,
    get_latest_message,
    update_last_read,
    get_unread_count,
    get_total_unread_count,
    search_users,
)
from app.utils.time_utils import get_current_utc_time
import pandas as pd
from typing import Optional
from app.db.core.models.user_data_models import User
from app.utils.serialize_output import serialize_sqlalchemy_obj
from uuid import UUID

# Reason: Threshold accounts for floating-point precision while detecting meaningful drift
DRIFT_THRESHOLD = 0.00005 # -> 5%
DRAWDOWN_THRESHOLD = -0.10 # -> 10%
PROPHITAI_SYSTEM_USER_ID = UUID("e7ab723f-a415-4f3c-8445-4eaf08cf605e")

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

    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        self._user_session: UserSession | None = None
        self._market_session: MarketSession | None = None
        self._preferences: Dict[str, float] | None = None
        self._positions: Dict[str, float] | None = None
        self._portfolio_created_date: datetime | None = None
        self._user_id: UUID | None = None

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
            Portfolio.user_id
        ).filter(
            Portfolio.id == self.portfolio_id
        ).first()
        if portfolio_row:
            self._portfolio_created_date = portfolio_row.created_date
            self._user_id = portfolio_row.user_id
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
        drift_result = detect_allocation_drift(self.positions, self.preferences, self.market_session)
        drawdown_result = detect_drawdowns(self.positions, self.portfolio_created_date)
        correlations = detect_portfolio_correlation_change(self.positions)
        pair_correlations = detect_pair_correlation_changes(self.positions)

        print(correlations.triggered)
        print(pair_correlations.triggered)
        # print(pair_correlations.pairs)
        print(pair_correlations.flagged_pairs)
        print(drift_result.triggered)
        print(drawdown_result.triggered)

#         if drift_result.triggered or drawdown_result.triggered:
#             # Get or create conversation between system and user
#             conversation = get_or_create_conversation(
#                 user_1_id=PROPHITAI_SYSTEM_USER_ID,
#                 user_2_id=self.user_id
#             )

#             # message keys: [@portfolio_name](portfolio:portfolio_id)
#             # ticker keys: [#ticker_name](ticker:ticker_symbol:asset_type)
#             # [&watchlist name](watchlist:watchlist_id)

#             message_content = f"""
# 🚨 Alert 🚨

# Portfolio Drawdown Detected:
# - {len(drawdown_result.flagged_positions)} positions have drawdowns exceeding threshold.
# - Please monitor [#TSLA](ticker:TSLA:equity)

# Portfolio Allocation Drift Detected:
# - {len(drift_result.flagged_sectors)} sectors have allocations exceeding threshold.
# - Please monitor [#CRWV](ticker:CRWV:equity)

# Portfolio in Danger Zone:
# - [@MAGGIES AWESOME PORTFOLIO](portfolio:2b954a4b-5686-48f4-932f-c36ae6ab6078)
#             """

#             # Send notification
#             create_message(
#                 conversation_id=conversation.id,
#                 sender_id=PROPHITAI_SYSTEM_USER_ID,
#                 content=message_content
#             )

        return drift_result, drawdown_result

if __name__ == "__main__":
    with MonitorPortfolio(portfolio_id="9460b73c-ff64-40aa-8af4-139f55a5a45a") as monitor:
        monitor.notify()

    # with UserSession() as user_session:
    #     user = user_session.query(User).filter(User.email == "michaellaret7@gmail.com").first()
    #     if user:
    #         portfolios = user_session.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    #         for p in portfolios:
    #             print(serialize_sqlalchemy_obj(p))
    
    # # with UserSession() as user_session:
    # #     user = user_session.query(User).filter(User.email == "michaellaret7@gmail.com").first()

    # #     if user:
    # #         print(serialize_sqlalchemy_obj(user))
        
