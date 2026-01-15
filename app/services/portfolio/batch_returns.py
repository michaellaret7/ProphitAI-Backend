"""
Batch portfolio returns service with shared price data.

This module provides efficient batch computation of returns for multiple portfolios
by fetching price data once for all unique tickers across portfolios.
"""
from typing import Dict, Any, List
import uuid
from datetime import timedelta

import pandas as pd
import numpy as np
from sqlalchemy.orm import joinedload

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio
from app.utils.time_utils import get_current_utc_time
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.returns.calculator import PortfolioReturnsCalculator


class BatchPortfolioReturnsService:
    """
    Service to compute returns for multiple portfolios with shared price data.

    Optimizes dashboard loading by:
    1. Single DB query to get all portfolios with positions
    2. Single price fetch for all unique tickers across portfolios (with returns=True)
    3. Build shared returns DataFrame once
    4. Calculate weighted returns per portfolio from shared DataFrame

    Args:
        portfolio_ids: List of portfolio UUIDs to compute returns for
        years: Number of years of historical data (default 3)
        initial_nav: Starting NAV value for each portfolio (default $1,000,000)
    """

    def __init__(
        self,
        portfolio_ids: List[str],
        years: int = 3,
        initial_nav: float = 1_000_000
    ):
        self.portfolio_ids = portfolio_ids
        self.years = years
        self.initial_nav = initial_nav

        # Precomputed state
        self.portfolios: Dict[str, Dict[str, Any]] = {}  # portfolio_id -> {weights, name, nav}
        self.unique_tickers: List[str] = []
        self.returns_df: pd.DataFrame = pd.DataFrame()  # Shared returns DataFrame

        # Precompute all shared data
        self._load_all_portfolios()
        self._fetch_and_build_returns_df()

    def _load_all_portfolios(self) -> None:
        """
        Load all portfolios with positions in a single query.

        Builds a dict mapping portfolio_id to weights and metadata.
        Also collects all unique tickers across portfolios.
        """
        if not self.portfolio_ids:
            return

        # Convert string IDs to UUIDs
        uuid_ids = [uuid.UUID(pid) if isinstance(pid, str) else pid for pid in self.portfolio_ids]

        with UserSession() as session:
            # Single query with joinedload to avoid N+1
            portfolios = session.query(Portfolio).options(
                joinedload(Portfolio.items)
            ).filter(Portfolio.id.in_(uuid_ids)).all()

            all_tickers = set()

            for portfolio in portfolios:
                portfolio_id = str(portfolio.id)
                weights = {}

                for item in portfolio.items:
                    if item.ticker and item.allocation is not None:
                        weights[item.ticker] = float(item.allocation)
                        all_tickers.add(item.ticker)

                if weights:
                    self.portfolios[portfolio_id] = {
                        'weights': weights,
                        'name': portfolio.name,
                        'nav': portfolio.nav,
                    }

            self.unique_tickers = list(all_tickers)

    def _fetch_and_build_returns_df(self) -> None:
        """
        Fetch OHLCV data with returns=True and build shared returns DataFrame.

        Uses fetch_bulk_ohlcv_data_for_tickers which internally parallelizes
        the price fetches with ThreadPoolExecutor(max_workers=20).

        The returns DataFrame has tickers as columns and dates as index,
        with each cell containing the daily return for that ticker on that date.
        """
        if not self.unique_tickers:
            return

        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=365 * self.years)

        # Fetch OHLCV data with pre-calculated returns
        price_data = fetch_bulk_ohlcv_data_for_tickers(
            tickers=self.unique_tickers,
            start_date_str=start_date.strftime('%Y-%m-%d'),
            end_date_str=end_date.strftime('%Y-%m-%d'),
            frequency='daily',
            returns=True
        )

        if not price_data:
            return

        # Build returns DataFrame from the 'returns' column of each ticker's data
        returns_series = {
            ticker: data['returns']
            for ticker, data in price_data.items()
            if 'returns' in data.columns
        }

        if not returns_series:
            return

        self.returns_df = pd.concat(returns_series, axis=1)
        self.returns_df.index = pd.to_datetime(self.returns_df.index)
        self.returns_df.sort_index(inplace=True)

    def _calculate_portfolio_returns(self, portfolio_id: str) -> Dict[str, Any]:
        """
        Calculate returns for a single portfolio using shared returns DataFrame.

        Args:
            portfolio_id: UUID of the portfolio

        Returns:
            Dict with 'returns_series' and 'summary_metrics'
        """
        portfolio_data = self.portfolios.get(portfolio_id)
        if not portfolio_data:
            return {'returns_series': [], 'summary_metrics': {}}

        if self.returns_df.empty:
            return {'returns_series': [], 'summary_metrics': {}}

        weights = portfolio_data['weights']

        # Filter returns DataFrame to only tickers in this portfolio
        available_tickers = [t for t in weights if t in self.returns_df.columns]
        if not available_tickers:
            return {'returns_series': [], 'summary_metrics': {}}

        # Build ticker returns dict from the shared DataFrame
        portfolio_ticker_returns = {
            ticker: self.returns_df[ticker]
            for ticker in available_tickers
        }

        # Calculate weighted portfolio returns
        daily_returns = PortfolioReturnsCalculator.weighted_daily_returns(
            portfolio_ticker_returns,
            weights,
            dropna=False,
            renormalize_each_day=True
        )

        if daily_returns.empty:
            return {'returns_series': [], 'summary_metrics': {}}

        # Calculate cumulative returns and NAV
        cumulative_returns = (1 + daily_returns).cumprod()
        nav_progression = cumulative_returns * self.initial_nav

        # Format returns series
        returns_series = [
            {
                "date": (date if date.tz else pd.Timestamp(date, tz='UTC')).isoformat(),
                "cumulativeReturn": float(cum_ret) if np.isfinite(cum_ret) else None,
                "nav": float(nav) if np.isfinite(nav) else None
            }
            for date, cum_ret, nav in zip(
                cumulative_returns.index,
                cumulative_returns.values,
                nav_progression.values
            )
        ]

        # Calculate summary metrics
        summary_metrics = self._calculate_summary_metrics(daily_returns, cumulative_returns)

        return {
            'returns_series': returns_series,
            'summary_metrics': summary_metrics
        }

    def _calculate_summary_metrics(
        self,
        daily_returns: pd.Series,
        cumulative_returns: pd.Series
    ) -> Dict[str, float]:
        """Calculate summary performance metrics for a portfolio."""
        if daily_returns.empty:
            return {}

        trading_days = 252

        # Total return
        total_return = float(cumulative_returns.iloc[-1] - 1) if len(cumulative_returns) > 0 else 0.0

        # Annualized return
        n_days = len(daily_returns)
        years = n_days / trading_days
        if years > 0 and total_return > -1:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = daily_returns.mean() * trading_days

        # Volatility
        annual_volatility = daily_returns.std() * np.sqrt(trading_days)

        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0

        # Max drawdown
        if not cumulative_returns.empty:
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
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

    def get_all_returns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get returns series for all portfolios.

        Returns:
            Dict mapping portfolio_id to list of return data points.
            Each data point has 'date', 'cumulativeReturn', and 'nav'.
        """
        results = {}

        for portfolio_id in self.portfolios:
            portfolio_returns = self._calculate_portfolio_returns(portfolio_id)
            results[portfolio_id] = portfolio_returns['returns_series']

        return results

    def get_all_returns_with_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get returns series and summary metrics for all portfolios.

        Returns:
            Dict mapping portfolio_id to dict with 'returns_series' and 'summary_metrics'.
        """
        results = {}

        for portfolio_id in self.portfolios:
            results[portfolio_id] = self._calculate_portfolio_returns(portfolio_id)

        return results
