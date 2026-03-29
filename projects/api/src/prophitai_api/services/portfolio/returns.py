from typing import Dict, Any, List, Optional
import uuid
from datetime import timedelta
import pandas as pd
import numpy as np
from prophitai_data.repositories.portfolio.retrieval import retrieve_portfolio
from prophitai_shared.time_utils import get_current_utc_time
from prophitai_data.repositories.price import fetch_bulk_price_data_for_tickers
from prophitai_calculations.performance.returns import calc_annualized_return, calc_cumulative_total_return
from prophitai_calculations.performance.ratios import calc_sharpe_ratio
from prophitai_calculations.risk.distribution import calc_volatility
from prophitai_calculations.risk.drawdown import calc_max_drawdown


class PortfolioReturnsService:
    """
    Service to compute portfolio returns, NAV progression, and performance metrics.

    Precomputes all calculations in __init__ for performance optimization.

    Supports two modes:
    - DB mode: pass portfolio_id + email to load positions from database
    - Direct mode: pass tickers + weights to skip DB lookup (e.g. from live broker positions)

    Precomputed attributes:
    - positions: List of portfolio positions
    - weights: Dict of ticker -> allocation (as decimal)
    - daily_returns: Portfolio daily returns series
    - cumulative_returns: Cumulative returns series
    - nav_progression: NAV progression series (starting at initial_nav)

    Args:
        portfolio_id: UUID of the portfolio (DB mode)
        tickers: List of ticker symbols (direct mode)
        weights: Dict of ticker -> weight as decimal (direct mode)
        years: Number of years of historical data (default 2)
        email: Optional email for portfolio retrieval (DB mode)
        initial_nav: Starting NAV value (default $1,000,000)
    """

    def __init__(
        self,
        portfolio_id: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        years: int = 2,
        email: Optional[str] = None,
        initial_nav: float = 1_000_000,
    ):
        self.portfolio_id = portfolio_id
        self.years = years
        self.email = email or "michaellaret7@gmail.com"
        self.initial_nav = initial_nav

        # Initialize empty state
        self.positions: List[Dict[str, Any]] = []
        self.weights: Dict[str, float] = {}
        self.price_data: pd.DataFrame = pd.DataFrame()
        self.daily_returns: pd.Series = pd.Series(dtype=float)
        self.cumulative_returns: pd.Series = pd.Series(dtype=float)
        self.nav_progression: pd.Series = pd.Series(dtype=float)

        # Reason: Support both direct tickers+weights and DB portfolio lookup
        if tickers and weights:
            self.positions = [{"ticker": t, "allocation": w} for t, w in weights.items()]
            self.weights = weights
        elif portfolio_id:
            self._load_positions()
        else:
            raise ValueError("Either portfolio_id or (tickers, weights) required")

        # Precompute all calculations
        self._fetch_price_data()
        self._calculate_returns()
        self._calculate_nav()

    def _load_positions(self) -> None:
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
                weights[ticker] = float(allocation)

        if not weights:
            raise ValueError("Portfolio has no valid positions")

        self.weights = weights

    def _fetch_price_data(self) -> None:
        """
        Fetch historical price data for all portfolio tickers.

        Raises:
            ValueError: If unable to fetch price data
        """
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=365 * self.years)

        tickers = list(self.weights.keys())
        ticker_closes = fetch_bulk_price_data_for_tickers(
            tickers=tickers,
            start_date_str=start_date.strftime('%Y-%m-%d'),
            end_date_str=end_date.strftime('%Y-%m-%d'),
            frequency='daily'
        )

        if ticker_closes.empty:
            raise ValueError("Unable to fetch price data for portfolio")

        self.price_data = ticker_closes

    def _calculate_returns(self) -> None:
        """Calculate portfolio daily returns using weighted average of ticker returns."""
        available = [t for t in self.weights if t in self.price_data.columns]
        asset_returns = self.price_data[available].pct_change(fill_method=None).dropna()

        weights_series = pd.Series({t: self.weights[t] for t in available})
        self.daily_returns = asset_returns.dot(weights_series)

    def _calculate_nav(self) -> None:
        """Calculate cumulative returns and NAV progression."""
        if self.daily_returns.empty:
            return

        self.cumulative_returns = (1 + self.daily_returns).cumprod()
        self.nav_progression = self.cumulative_returns * self.initial_nav

    def get_returns_series(self) -> List[Dict[str, Any]]:
        """
        Get formatted time series of returns and NAV for API response.

        Returns:
            List of dicts with 'date', 'cumulativeReturn', and 'nav' keys
        """
        if self.cumulative_returns.empty:
            return []

        return [
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

    def get_summary_metrics(self) -> Dict[str, float]:
        """
        Get summary performance metrics.

        Returns:
            Dict with total_return, annualized_return, volatility, sharpe_ratio, max_drawdown
        """
        if self.daily_returns.empty:
            return {}

        total_return = calc_cumulative_total_return(self.daily_returns)
        annualized_return = calc_annualized_return(self.daily_returns)
        volatility = calc_volatility(self.daily_returns, annualize=True)
        sharpe = calc_sharpe_ratio(self.daily_returns)
        max_dd = calc_max_drawdown(self.daily_returns)

        return {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(annualized_return * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe, 3) if sharpe is not None else 0,
            'max_drawdown': round(max_dd * 100, 2),
        }
