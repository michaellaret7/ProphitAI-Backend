from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.repositories.portfolio_data import retrieve_portfolio
from app.utils.time_utils import get_current_utc_time
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.returns.calculator import PortfolioReturnsCalculator, ReturnsCalculator


class PortfolioReturnsService:
    """
    Service to compute portfolio returns, NAV progression, and performance metrics.

    Follows ProphitAltsServices pattern - precomputes all calculations in __init__
    for performance optimization. This service is initialized once per request and
    provides fast accessor methods for precomputed results.

    Precomputed attributes:
    - positions: List of portfolio positions
    - weights: Dict of ticker -> allocation (as decimal)
    - daily_returns: Portfolio daily returns series
    - cumulative_returns: Cumulative returns series
    - nav_progression: NAV progression series (starting at initial_nav)

    Args:
        portfolio_id: UUID of the portfolio
        years: Number of years of historical data (default 2)
        email: Optional email for portfolio retrieval
        initial_nav: Starting NAV value (default $1,000,000)
    """

    def __init__(
        self,
        portfolio_id: str,
        years: int = 2,
        email: Optional[str] = None,
        initial_nav: float = 1_000_000
    ):
        self.portfolio_id = portfolio_id
        self.years = years
        self.email = email or "michaellaret7@gmail.com"  # Default email for now
        self.initial_nav = initial_nav

        # Initialize empty state
        self.positions: List[Dict[str, Any]] = []
        self.weights: Dict[str, float] = {}
        self.price_data: Dict[str, pd.Series] = {}
        self.daily_returns: pd.Series = pd.Series(dtype=float)
        self.cumulative_returns: pd.Series = pd.Series(dtype=float)
        self.nav_progression: pd.Series = pd.Series(dtype=float)

        # Precompute all calculations
        self._load_positions()
        self._fetch_price_data()
        self._calculate_returns()
        self._calculate_nav()

    def _load_positions(self):
        """
        Load portfolio positions from repository and build weights dict.

        Raises:
            ValueError: If portfolio not found or has no valid positions
        """
        positions = retrieve_portfolio(
            email=self.email,
            portfolio_id=uuid.UUID(self.portfolio_id)
        )

        if not positions:
            raise ValueError("Portfolio not found")

        self.positions = positions

        # Build weights dictionary (allocation already in decimal format)
        weights = {}
        for pos in positions:
            ticker = pos.get('ticker')
            allocation = pos.get('allocation')
            if ticker and allocation is not None:
                weights[ticker] = float(allocation)  # Already decimal (0.25 = 25%)

        if not weights:
            raise ValueError("Portfolio has no valid positions")

        self.weights = weights

    def _fetch_price_data(self):
        """
        Fetch historical price data for all portfolio tickers.

        Raises:
            ValueError: If unable to fetch price data
        """
        # Calculate date range (using UTC time)
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=365 * self.years)

        # Fetch bulk price data
        tickers = list(self.weights.keys())
        ticker_closes = fetch_bulk_price_data_for_tickers(
            tickers=tickers,
            start_date_str=start_date.strftime('%Y-%m-%d'),
            end_date_str=end_date.strftime('%Y-%m-%d'),
            frequency='daily'
        )

        if not ticker_closes:
            raise ValueError("Unable to fetch price data for portfolio")

        self.price_data = ticker_closes

    def _calculate_returns(self):
        """
        Calculate portfolio daily returns using weighted average of ticker returns.

        Uses core calculations library (ReturnsCalculator, PortfolioReturnsCalculator)
        to compute returns with day-by-day renormalization for missing data.
        """
        # Calculate daily returns for each ticker
        ticker_price_returns = {
            ticker: ReturnsCalculator.daily_price_returns(self.price_data[ticker])
            for ticker in self.weights if ticker in self.price_data
        }

        # Calculate weighted portfolio returns
        # Uses renormalize_each_day=True to handle missing data
        portfolio_daily = PortfolioReturnsCalculator.weighted_daily_returns(
            ticker_price_returns,
            self.weights,
            dropna=False,
            renormalize_each_day=True
        )

        self.daily_returns = portfolio_daily

    def _calculate_nav(self):
        """
        Calculate cumulative returns and NAV progression.

        NAV progression starts at initial_nav and compounds daily returns.
        """
        if self.daily_returns.empty:
            return

        # Calculate cumulative returns
        self.cumulative_returns = (1 + self.daily_returns).cumprod()

        # Calculate NAV progression starting at initial NAV
        self.nav_progression = self.cumulative_returns * self.initial_nav

    def get_returns_series(self) -> List[Dict[str, Any]]:
        """
        Get formatted time series of returns and NAV for API response.

        Returns:
            List of dicts with 'date', 'cumulativeReturn', and 'nav' keys
        """
        if self.cumulative_returns.empty:
            return []

        returns_data = [
            {
                "date": (date if date.tz else pd.Timestamp(date, tz='UTC')).isoformat(),
                "cumulativeReturn": float(cum_ret) if np.isfinite(cum_ret) else None,
                "nav": float(nav) if np.isfinite(nav) else None
            }
            for date, cum_ret, nav in zip(
                self.cumulative_returns.index,
                self.cumulative_returns.values,
                self.nav_progression.values
            )
        ]

        return returns_data

    def get_summary_metrics(self) -> Dict[str, float]:
        """
        Get summary performance metrics.

        Returns:
            Dict with total_return, annualized_return, volatility, sharpe_ratio, etc.
        """
        if self.daily_returns.empty:
            return {}

        trading_days = 252

        # Total return
        total_return = float(self.cumulative_returns.iloc[-1] - 1) if len(self.cumulative_returns) > 0 else 0.0

        # Annualized return
        n_days = len(self.daily_returns)
        years = n_days / trading_days
        if years > 0 and total_return > -1:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = self.daily_returns.mean() * trading_days

        # Volatility
        annual_volatility = self.daily_returns.std() * np.sqrt(trading_days)

        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0

        # Max drawdown
        if not self.cumulative_returns.empty:
            running_max = self.cumulative_returns.expanding().max()
            drawdown = (self.cumulative_returns - running_max) / running_max
            max_drawdown = float(drawdown.min())
        else:
            max_drawdown = 0.0

        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'volatility': round(annual_volatility * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'max_drawdown': round(max_drawdown * 100, 2),
        }
