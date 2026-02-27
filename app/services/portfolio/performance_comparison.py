"""
Service to compute performance comparison between current portfolio, optimized portfolio, and SPY.

This service is used after portfolio optimization to provide comprehensive performance metrics,
including returns comparison, underwater charts (drawdowns), and risk/performance metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import timedelta
import uuid
import pandas as pd
import numpy as np
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_current_utc_time
from app.repositories.portfolio.retrieval import retrieve_portfolio
from app.core.calculations.performance.returns import calc_annualized_return
from app.core.calculations.performance.ratios import calc_sharpe_ratio, calc_sortino_ratio
from app.core.calculations.risk.distribution import calc_volatility, calc_var
from app.core.calculations.risk.drawdown import calc_max_drawdown


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
        self.optimized_weights = optimized_weights  # Already decimal format (0.25 = 25%)
        self.years = years

        # Initialize state
        self.current_weights: Dict[str, float] = {}
        self.price_data: pd.DataFrame = pd.DataFrame()
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

        # Build weights dictionary (allocation already in decimal format)
        weights = {}
        for pos in positions:
            ticker = pos.get('ticker')
            allocation = pos.get('allocation')
            if ticker and allocation is not None:
                weights[ticker] = float(allocation)  # Already decimal (0.25 = 25%)

        if not weights:
            raise ValueError("Portfolio has no valid positions")

        self.current_weights = weights

    def _fetch_price_data(self):
        """
        Fetch historical price data for all portfolio tickers and SPY.

        Raises:
            ValueError: If unable to fetch price data
        """
        # Calculate date range (using UTC time)
        end_date = get_current_utc_time()
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

        if ticker_closes.empty:
            raise ValueError("Unable to fetch price data")

        # Separate SPY from portfolio tickers
        self.spy_prices = ticker_closes['SPY'] if 'SPY' in ticker_closes.columns else pd.Series(dtype=float)
        self.price_data = ticker_closes.drop(columns=['SPY'], errors='ignore')

    def _calculate_returns(self) -> None:
        """Calculate daily returns for current portfolio, optimized portfolio, and SPY."""
        asset_returns = self.price_data.pct_change().dropna()

        # Current portfolio weighted returns
        current_tickers = [t for t in self.current_weights if t in asset_returns.columns]
        current_w = pd.Series({t: self.current_weights[t] for t in current_tickers})
        self.current_returns = asset_returns[current_tickers].dot(current_w)

        # Optimized portfolio weighted returns
        opt_tickers = [t for t in self.optimized_weights if t in asset_returns.columns]
        opt_w = pd.Series({t: self.optimized_weights[t] for t in opt_tickers})
        self.optimized_returns = asset_returns[opt_tickers].dot(opt_w)

        # SPY returns
        self.spy_returns = self.spy_prices.pct_change().dropna()

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

        Args:
            daily_returns: Daily returns series

        Returns:
            Dict with sharpeRatio, sortinoRatio, maxDrawdown, annualizedReturn, annualizedVolatility, var95
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

        ann_ret = calc_annualized_return(daily_returns)
        ann_vol = calc_volatility(daily_returns, annualize=True)
        sharpe = calc_sharpe_ratio(daily_returns)
        sortino = calc_sortino_ratio(daily_returns)
        max_dd = calc_max_drawdown(daily_returns)
        var_95 = calc_var(daily_returns, confidence=0.95)

        return {
            "sharpeRatio": round(sharpe, 2) if sharpe is not None else 0.0,
            "sortinoRatio": round(sortino, 2) if sortino is not None else 0.0,
            "maxDrawdown": round(max_dd * 100, 1),
            "annualizedReturn": round(ann_ret * 100, 1),
            "annualizedVolatility": round(ann_vol * 100, 1),
            "var95": round(var_95 * 100, 1),
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
