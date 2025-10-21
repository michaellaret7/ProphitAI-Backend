"""
Service to compute performance comparison between current portfolio, optimized portfolio, and SPY.

This service is used after portfolio optimization to provide comprehensive performance metrics,
including returns comparison, underwater charts (drawdowns), and risk/performance metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import pandas as pd
import numpy as np
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.repositories.portfolio_data import retrieve_portfolio
from app.core.calculations.returns.calculator import PortfolioReturnsCalculator, ReturnsCalculator


class PortfolioPerformanceComparisonService:
    """
    Service to calculate and compare performance metrics between portfolios.

    Compares:
    - Current portfolio (fetched from portfolio_id)
    - Optimized portfolio (new allocations)
    - SPY benchmark

    Calculates:
    - Returns time series (indexed to 100)
    - Drawdown time series (underwater chart)
    - Risk & performance metrics (Sharpe, Sortino, volatility, VaR, max drawdown, returns)

    Args:
        portfolio_id: UUID of the current portfolio
        optimized_weights: Dict of ticker -> allocation (as percentage, e.g., 10.5)
        years: Number of years of historical data (default 2)
        email: Optional email for portfolio retrieval
    """

    def __init__(
        self,
        portfolio_id: str,
        optimized_weights: Dict[str, float],
        years: int = 2,
        email: Optional[str] = None,
    ):
        self.portfolio_id = portfolio_id
        self.email = email or "michaellaret7@gmail.com"
        self.optimized_weights = {k: v / 100.0 for k, v in optimized_weights.items()}
        self.years = years

        # Initialize state
        self.current_weights: Dict[str, float] = {}
        self.price_data: Dict[str, pd.Series] = {}
        self.spy_prices: pd.Series = pd.Series(dtype=float)
        self.current_returns: pd.Series = pd.Series(dtype=float)
        self.optimized_returns: pd.Series = pd.Series(dtype=float)
        self.spy_returns: pd.Series = pd.Series(dtype=float)

        # Precompute all calculations
        self._load_current_portfolio()
        self._fetch_price_data()
        self._calculate_returns()

    def _load_current_portfolio(self):
        """
        Load current portfolio positions from repository and build weights dict.

        Raises:
            ValueError: If portfolio not found or has no valid positions
        """
        positions = retrieve_portfolio(
            email=self.email,
            portfolio_id=uuid.UUID(self.portfolio_id)
        )

        if not positions:
            raise ValueError("Portfolio not found")

        # Build weights dictionary (convert allocation percentage to decimal)
        weights = {}
        for pos in positions:
            ticker = pos.get('ticker')
            allocation = pos.get('allocation')
            if ticker and allocation is not None:
                weights[ticker] = float(allocation) / 100.0

        if not weights:
            raise ValueError("Portfolio has no valid positions")

        self.current_weights = weights

    def _fetch_price_data(self):
        """
        Fetch historical price data for all portfolio tickers and SPY.

        Raises:
            ValueError: If unable to fetch price data
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * self.years)

        # Get all unique tickers from both portfolios
        all_tickers = set(self.current_weights.keys()) | set(self.optimized_weights.keys())
        all_tickers.add('SPY')  # Add SPY for benchmark

        # Fetch bulk price data
        ticker_closes = fetch_bulk_price_data_for_tickers(
            tickers=list(all_tickers),
            start_date_str=start_date.strftime('%Y-%m-%d'),
            end_date_str=end_date.strftime('%Y-%m-%d'),
            frequency='daily'
        )

        if not ticker_closes:
            raise ValueError("Unable to fetch price data")

        # Separate SPY from portfolio tickers
        self.spy_prices = ticker_closes.pop('SPY', pd.Series(dtype=float))
        self.price_data = ticker_closes

    def _calculate_returns(self):
        """
        Calculate daily returns for current portfolio, optimized portfolio, and SPY.

        Uses core calculations library (ReturnsCalculator, PortfolioReturnsCalculator)
        to compute returns with day-by-day renormalization for missing data.
        """
        # Calculate daily returns for each ticker
        ticker_price_returns = {
            ticker: ReturnsCalculator.daily_price_returns(self.price_data[ticker])
            for ticker in self.price_data
        }

        # Calculate weighted portfolio returns for current portfolio
        current_daily = PortfolioReturnsCalculator.weighted_daily_returns(
            ticker_price_returns,
            self.current_weights,
            dropna=False,
            renormalize_each_day=True
        )

        # Calculate weighted portfolio returns for optimized portfolio
        optimized_daily = PortfolioReturnsCalculator.weighted_daily_returns(
            ticker_price_returns,
            self.optimized_weights,
            dropna=False,
            renormalize_each_day=True
        )

        # Calculate SPY returns
        spy_daily = ReturnsCalculator.daily_price_returns(self.spy_prices)

        self.current_returns = current_daily
        self.optimized_returns = optimized_daily
        self.spy_returns = spy_daily

    def _calculate_cumulative_returns(self, daily_returns: pd.Series) -> pd.Series:
        """Calculate cumulative returns from daily returns."""
        if daily_returns.empty:
            return pd.Series(dtype=float)
        return (1 + daily_returns).cumprod()

    def _calculate_drawdowns(self, cumulative_returns: pd.Series) -> pd.Series:
        """
        Calculate drawdown series (underwater chart data).

        Drawdown = (Current Value - Running Maximum) / Running Maximum
        """
        if cumulative_returns.empty:
            return pd.Series(dtype=float)

        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        return drawdown

    def _calculate_metrics(self, daily_returns: pd.Series) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.

        Metrics:
        - Sharpe ratio (risk-adjusted return)
        - Sortino ratio (downside risk-adjusted return)
        - Annualized return
        - Annualized volatility
        - Max drawdown
        - VaR (95%)

        Args:
            daily_returns: Daily returns series

        Returns:
            Dict with all performance metrics
        """
        if daily_returns.empty:
            return {
                "sharpeRatio": 0.0,
                "sortinoRatio": 0.0,
                "maxDrawdown": 0.0,
                "annualizedReturn": 0.0,
                "annualizedVolatility": 0.0,
                "var95": 0.0,
            }

        trading_days = 252
        risk_free_rate = 0.02

        # Cumulative returns for drawdown calculation
        cumulative_returns = self._calculate_cumulative_returns(daily_returns)

        # Annualized return
        n_days = len(daily_returns)
        years = n_days / trading_days
        total_return = float(cumulative_returns.iloc[-1] - 1) if len(cumulative_returns) > 0 else 0.0

        if years > 0 and total_return > -1:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = daily_returns.mean() * trading_days

        # Volatility
        annual_volatility = daily_returns.std() * np.sqrt(trading_days)

        # Sharpe ratio
        sharpe_ratio = (annualized_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0.0

        # Sortino ratio (downside deviation)
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(trading_days) if len(downside_returns) > 0 else 0.0
        sortino_ratio = (annualized_return - risk_free_rate) / downside_std if downside_std > 0 else 0.0

        # Max drawdown
        drawdowns = self._calculate_drawdowns(cumulative_returns)
        max_drawdown = float(drawdowns.min()) if not drawdowns.empty else 0.0

        # VaR (95% confidence)
        var_95_pct = daily_returns.quantile(0.05)

        return {
            "sharpeRatio": round(sharpe_ratio, 2),
            "sortinoRatio": round(sortino_ratio, 2),
            "maxDrawdown": round(max_drawdown * 100, 1),  # As percentage
            "annualizedReturn": round(annualized_return * 100, 1),  # As percentage
            "annualizedVolatility": round(annual_volatility * 100, 1),  # As percentage
            "var95": round(var_95_pct * 100, 1),  # As percentage
        }

    def get_returns_comparison(self) -> List[Dict[str, Any]]:
        """
        Get returns time series indexed to 100 for comparison chart.

        Returns:
            List of dicts with 'date', 'current', 'optimized', 'spy' keys
            Each value is indexed to 100 at the start
        """
        # Calculate cumulative returns
        current_cum = self._calculate_cumulative_returns(self.current_returns)
        optimized_cum = self._calculate_cumulative_returns(self.optimized_returns)
        spy_cum = self._calculate_cumulative_returns(self.spy_returns)

        if current_cum.empty:
            return []

        # Align all series to same date index
        aligned_df = pd.DataFrame({
            'current': current_cum,
            'optimized': optimized_cum,
            'spy': spy_cum
        }).dropna()

        # Index to 100
        indexed_df = aligned_df * 100

        # Convert to list of dicts
        returns_data = [
            {
                "date": (date if date.tz else pd.Timestamp(date, tz='UTC')).isoformat(),
                "current": float(row['current']) if np.isfinite(row['current']) else None,
                "optimized": float(row['optimized']) if np.isfinite(row['optimized']) else None,
                "spy": float(row['spy']) if np.isfinite(row['spy']) else None,
            }
            for date, row in indexed_df.iterrows()
        ]

        return returns_data

    def get_drawdowns_comparison(self) -> List[Dict[str, Any]]:
        """
        Get drawdown time series for underwater chart comparison.

        Returns:
            List of dicts with 'date', 'current', 'optimized' keys
            Each value is drawdown as percentage (negative values)
        """
        # Calculate cumulative returns
        current_cum = self._calculate_cumulative_returns(self.current_returns)
        optimized_cum = self._calculate_cumulative_returns(self.optimized_returns)

        # Calculate drawdowns
        current_dd = self._calculate_drawdowns(current_cum)
        optimized_dd = self._calculate_drawdowns(optimized_cum)

        if current_dd.empty:
            return []

        # Align both series to same date index
        aligned_df = pd.DataFrame({
            'current': current_dd,
            'optimized': optimized_dd
        }).dropna()

        # Convert to percentage
        aligned_df = aligned_df * 100

        # Convert to list of dicts
        drawdowns_data = [
            {
                "date": (date if date.tz else pd.Timestamp(date, tz='UTC')).isoformat(),
                "current": float(row['current']) if np.isfinite(row['current']) else None,
                "optimized": float(row['optimized']) if np.isfinite(row['optimized']) else None,
            }
            for date, row in aligned_df.iterrows()
        ]

        return drawdowns_data

    def get_metrics_comparison(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics comparison between portfolios and SPY.

        Returns:
            Dict with 'current', 'optimized', and 'spy' metrics
        """
        current_metrics = self._calculate_metrics(self.current_returns)
        optimized_metrics = self._calculate_metrics(self.optimized_returns)

        # For SPY, calculate simple total return
        spy_cum = self._calculate_cumulative_returns(self.spy_returns)
        spy_total_return = float((spy_cum.iloc[-1] - 1) * 100) if len(spy_cum) > 0 else 0.0

        return {
            "current": current_metrics,
            "optimized": optimized_metrics,
            "spy": {
                "totalReturn": round(spy_total_return, 1)
            }
        }

    def get_performance_data(self) -> Dict[str, Any]:
        """
        Get complete performance comparison data for API response.

        Returns:
            Dict with 'returns', 'drawdowns', and 'metrics' keys
        """
        return {
            "returns": self.get_returns_comparison(),
            "drawdowns": self.get_drawdowns_comparison(),
            "metrics": self.get_metrics_comparison()
        }
