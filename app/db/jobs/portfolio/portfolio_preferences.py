"""
Portfolio preference monitoring and drift detection.

This module provides functionality to monitor portfolio allocations against
user-defined preferences and detect when actual allocations have drifted
from target allocations.
"""
from datetime import datetime
from typing import Any, Dict, Tuple

from app.db.core.db_config import UserSession, MarketSession
from app.db.core.models.user_data_models import Portfolio, PortfolioItem, PortfolioPreference
from app.db.jobs.portfolio.utils import classify_and_add_tickers
from app.repositories.price_data import fetch_bulk_price_data_for_tickers, fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_current_utc_time
import pandas as pd
from typing import Optional

# Reason: Threshold accounts for floating-point precision while detecting meaningful drift
DRIFT_THRESHOLD = 0.00005 # -> 5%

class MonitorPortfolio:
    """
    Monitor portfolio allocations and detect drift from preferences.

    This class compares current portfolio allocations against user-defined
    target allocations to identify sectors that have drifted beyond acceptable
    thresholds.

    Usage:
        with MonitorPortfolio(portfolio_id) as monitor:
            has_drift, drifted_sectors = monitor.detect_allocation_drift()
    """

    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        self._user_session: UserSession | None = None
        self._market_session: MarketSession | None = None
        self._preferences: Dict[str, float] | None = None
        self._positions: Dict[str, float] | None = None
        self._portfolio_created_date: datetime | None = None

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

        # Reason: Fetch portfolio creation date for downstream calculations
        portfolio_row = self._user_session.query(Portfolio.created_date).filter(
            Portfolio.id == self.portfolio_id
        ).first()
        if portfolio_row:
            self._portfolio_created_date = portfolio_row.created_date
        else:
            raise ValueError(f"No portfolio found with id {self.portfolio_id}")

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

    def detect_allocation_drift(self) -> Tuple[bool, Dict[str, dict]]:
        """
        Detect if portfolio allocations have drifted from target preferences.

        Returns:
            Tuple containing:
                - has_drift: True if any sector has drifted beyond threshold
                - drifted_sectors: Dict of sectors with drift details including
                  current_allocation, target_allocation, and drift amount
        """
        allocations = classify_and_add_tickers(self.positions, self.market_session)

        drifted_sectors = {}
        for sector, allocation in allocations.items():
            preference = self.preferences.get(sector, 0.0)
            diff = allocation - preference
            if abs(diff) > DRIFT_THRESHOLD:
                drifted_sectors[sector] = {
                    "current_allocation": allocation,
                    "target_allocation": preference,
                    "drift": diff
                }

        has_drift = len(drifted_sectors) > 0

        return has_drift, drifted_sectors
    
    def detect_drawdowns(self, threshold: float = -0.10) -> Dict[str, Any]:
        """
        Detect positions currently in drawdown below threshold.
        Returns only flagged positions that breach the threshold.
        """
        price_data = fetch_bulk_ohlcv_data_for_tickers(
            tickers=self.positions.keys(),
            start_date_str=self.portfolio_created_date.strftime('%Y-%m-%d'),
            end_date_str=get_current_utc_time().strftime('%Y-%m-%d'),
            frequency='daily',
            returns=True
        )
        
        returns_df = pd.DataFrame()
        for ticker, data in price_data.items():
            returns_df[ticker] = data['returns']
        returns_df = returns_df.dropna()
        
        # Cumulative wealth index
        cumulative_wealth = (1 + returns_df).cumprod()
        
        # High water mark and drawdown series
        high_water_mark = cumulative_wealth.cummax()
        drawdown_series = (cumulative_wealth - high_water_mark) / high_water_mark
        
        # Current and max drawdowns
        current_drawdowns = drawdown_series.iloc[-1]
        max_drawdowns = drawdown_series.min()
        
        # Only flagged positions (convert to native Python floats)
        flagged_positions = {
            ticker: {
                'current_drawdown': float(current_drawdowns[ticker]),
                'max_drawdown': float(max_drawdowns[ticker]),
                'peak_date': cumulative_wealth[ticker].idxmax().strftime('%Y-%m-%d'),
            }
            for ticker in current_drawdowns.index
            if current_drawdowns[ticker] < threshold
        }
        
        return {
            'flagged_positions': flagged_positions,
            'needs_reevaluation': len(flagged_positions) > 0,
            'threshold': threshold
        }

    def detect_positions_to_reevaluate(self, loss_threshold: float = -0.05) -> Dict[str, Any]:
        """
        Flag positions that are underwater (negative total return from entry).
        More appropriate for portfolio monitoring than drawdown from peak.
        """
        price_data = fetch_bulk_ohlcv_data_for_tickers(
            tickers=self.positions.keys(),
            start_date_str="2023-01-01", # self.portfolio_created_date.strftime('%Y-%m-%d'),
            end_date_str=get_current_utc_time().strftime('%Y-%m-%d'),
            frequency='daily',
            returns=True
        )
        
        returns_df = pd.DataFrame()
        for ticker, data in price_data.items():
            returns_df[ticker] = data['returns']
        returns_df = returns_df.dropna()
        
        # Cumulative wealth index
        cumulative_wealth = (1 + returns_df).cumprod()
        
        # Total return from entry (what actually matters for a portfolio)
        total_returns = cumulative_wealth.iloc[-1] - 1
        
        # Flag positions that are actually losing money
        flagged_positions = {
            ticker: {
                'total_return': float(total_returns[ticker]),
            }
            for ticker in total_returns.index
            if total_returns[ticker] < loss_threshold
        }
        
        return {
            'flagged_positions': flagged_positions,
            'needs_reevaluation': len(flagged_positions) > 0,
            'threshold': loss_threshold
        }

        

if __name__ == "__main__":
    with MonitorPortfolio(portfolio_id="9460b73c-ff64-40aa-8af4-139f55a5a45a") as monitor:
        # print(monitor.detect_allocation_drift())
        print(monitor.detect_positions_to_reevaluate())
