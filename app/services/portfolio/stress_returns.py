from typing import Dict, Any, Literal
from datetime import datetime
import pandas as pd
import numpy as np
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.returns.calculator import PortfolioReturnsCalculator, ReturnsCalculator


class StressReturnsService:
    """
    Service to compute portfolio and SPY returns at different frequencies for stress testing.

    Returns portfolio returns, SPY returns, and metrics for both (total return, volatility,
    max drawdown, Sharpe ratio) over a specific time period at daily, hourly, or 15-minute intervals.

    Args:
        weights: Dict mapping ticker to allocation in decimal format (e.g., {'AAPL': 0.5, 'MSFT': 0.5} for 50% each)
        start_date: Start date for analysis
        end_date: End date for analysis
        frequency: Time interval - 'daily', 'hourly', or '15mins'

    Example:
        >>> from datetime import datetime
        >>> service = StressReturnsService(
        ...     weights={'AAPL': 0.25, 'MSFT': 0.25, 'GOOGL': 0.25, 'AMZN': 0.25},  # Decimal format: 0.25 = 25%
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 3, 31),
        ...     frequency='daily'
        ... )
        >>> data = service.get_data()
        >>> print(data.keys())
        dict_keys(['portfolio_returns', 'spy_returns', 'portfolio_metrics', 'spy_metrics'])
    """

    def __init__(
        self,
        weights: Dict[str, float],
        start_date: datetime,
        end_date: datetime,
        frequency: Literal['daily', 'hourly', '15mins'] = 'daily'
    ):
        self.weights = weights
        self.start_date = start_date
        self.end_date = end_date
        self.frequency = frequency

        # Precomputed data
        self.portfolio_returns: pd.Series = pd.Series(dtype=float)
        self.spy_returns: pd.Series = pd.Series(dtype=float)

        # Run calculations
        self._fetch_price_data()
        self._calculate_returns()

    def _fetch_price_data(self):
        """Fetch price data for portfolio tickers and SPY."""
        # Weights are already in decimal form (0.25 = 25%)

        # Get all tickers including SPY
        tickers = list(self.weights.keys()) + ['SPY']

        # Fetch bulk price data at specified frequency
        self.price_data = fetch_bulk_price_data_for_tickers(
            tickers=tickers,
            start_date_str=self.start_date.strftime('%Y-%m-%d'),
            end_date_str=self.end_date.strftime('%Y-%m-%d'),
            frequency=self.frequency
        )

    def _calculate_returns(self):
        """Calculate returns for both portfolio and SPY."""
        # Calculate daily returns for each ticker
        ticker_returns = {
            ticker: ReturnsCalculator.daily_price_returns(self.price_data[ticker])
            for ticker in self.weights if ticker in self.price_data
        }

        # Calculate weighted portfolio returns
        self.portfolio_returns = PortfolioReturnsCalculator.weighted_daily_returns(
            ticker_returns,
            self.weights,
            dropna=False,
            renormalize_each_day=True
        )

        # Calculate SPY returns and align with portfolio returns index
        if 'SPY' in self.price_data and not self.price_data['SPY'].empty:
            # Get the union of all portfolio ticker price timestamps
            all_timestamps = self.portfolio_returns.index

            # Reindex SPY prices to match all portfolio timestamps
            # Use forward-fill first, then backward-fill for any remaining NaNs at the start
            spy_prices_aligned = self.price_data['SPY'].reindex(all_timestamps)
            spy_prices_aligned = spy_prices_aligned.bfill().ffill()

            # Calculate returns from aligned prices
            self.spy_returns = spy_prices_aligned.pct_change().fillna(0.0)
        else:
            # Create empty series with same index as portfolio
            self.spy_returns = pd.Series(0.0, index=self.portfolio_returns.index)

    def get_data(self) -> Dict[str, Any]:
        """
        Get portfolio returns, SPY returns, cumulative returns, and metrics for both.

        Returns:
            Dict with:
            - portfolio_returns: List of dicts with 'date', 'return', and 'cumulative_return' keys
            - spy_returns: List of dicts with 'date', 'return', and 'cumulative_return' keys
            - portfolio_metrics: Dict with total_return, volatility, max_drawdown, sharpe_ratio
            - spy_metrics: Dict with total_return, volatility, max_drawdown, sharpe_ratio
        """
        # Calculate cumulative returns
        portfolio_cumulative = (1 + self.portfolio_returns).cumprod()
        spy_cumulative = (1 + self.spy_returns).cumprod()

        # Format returns using the same index for both to ensure alignment
        # This guarantees both arrays have identical length and dates
        portfolio_data = []
        spy_data = []

        for date in self.portfolio_returns.index:
            # Add UTC timezone info if timestamp is naive
            date_with_tz = date if date.tz else pd.Timestamp(date, tz='UTC')

            portfolio_data.append({
                'date': date_with_tz.isoformat(),
                'return': float(self.portfolio_returns.loc[date]) if np.isfinite(self.portfolio_returns.loc[date]) else 0.0,
                'cumulative_return': float(portfolio_cumulative.loc[date] - 1) if np.isfinite(portfolio_cumulative.loc[date]) else 0.0
            })

            spy_data.append({
                'date': date_with_tz.isoformat(),
                'return': float(self.spy_returns.loc[date]) if np.isfinite(self.spy_returns.loc[date]) else 0.0,
                'cumulative_return': float(spy_cumulative.loc[date] - 1) if np.isfinite(spy_cumulative.loc[date]) else 0.0
            })

        # Calculate metrics for both portfolio and SPY
        portfolio_metrics = self._calculate_metrics(self.portfolio_returns)
        spy_metrics = self._calculate_metrics(self.spy_returns)

        return {
            'portfolio_returns': portfolio_data,
            'spy_returns': spy_data,
            'portfolio_metrics': portfolio_metrics,
            'spy_metrics': spy_metrics
        }

    def _calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate total return, volatility, max drawdown, and Sharpe ratio."""
        if returns.empty:
            return {
                'total_return': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            }

        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()

        # Total return over the period
        total_return = float(cumulative.iloc[-1] - 1) if len(cumulative) > 0 else 0.0

        # Volatility (annualized based on frequency)
        periods_per_year = self._get_periods_per_year()
        volatility = returns.std() * np.sqrt(periods_per_year)

        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        mean_return = returns.mean() * periods_per_year
        sharpe_ratio = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0.0

        # Max drawdown
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = float(drawdown.min())

        return {
            'total_return': float(round(total_return * 100, 2)),
            'volatility': float(round(volatility * 100, 2)),
            'max_drawdown': float(round(max_drawdown * 100, 2)),
            'sharpe_ratio': float(round(sharpe_ratio, 3))
        }

    def _get_periods_per_year(self) -> int:
        """Get number of periods per year based on frequency."""
        if self.frequency == 'daily':
            return 252
        elif self.frequency == 'hourly':
            return 252 * 6.5  # ~6.5 trading hours per day
        elif self.frequency == '15mins':
            return 252 * 6.5 * 4  # ~26 fifteen-minute periods per trading day
        return 252


if __name__ == "__main__":
    # Example usage - weights in decimal format (0.25 = 25%)
    weights = {'AAPL': 0.25, 'MSFT': 0.25, 'GOOGL': 0.25, 'AMZN': 0.25}
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 3, 31)
    frequency = '15mins'

    service = StressReturnsService(weights, start_date, end_date, frequency)
    data = service.get_data()

    print(f"\nPortfolio returns (first 5):")
    for item in data['portfolio_returns'][:5]:
        print(f"  {item['date']}: return={item['return']:.4%}, cumulative={item['cumulative_return']:.4%}")

    print(f"\nSPY returns (first 5):")
    for item in data['spy_returns'][:5]:
        print(f"  {item['date']}: return={item['return']:.4%}, cumulative={item['cumulative_return']:.4%}")

    print(f"\nPortfolio metrics:")
    print(f"  Total Return: {data['portfolio_metrics']['total_return']}%")
    print(f"  Volatility: {data['portfolio_metrics']['volatility']}%")
    print(f"  Max Drawdown: {data['portfolio_metrics']['max_drawdown']}%")
    print(f"  Sharpe Ratio: {data['portfolio_metrics']['sharpe_ratio']}")

    print(f"\nSPY metrics:")
    print(f"  Total Return: {data['spy_metrics']['total_return']}%")
    print(f"  Volatility: {data['spy_metrics']['volatility']}%")
    print(f"  Max Drawdown: {data['spy_metrics']['max_drawdown']}%")
    print(f"  Sharpe Ratio: {data['spy_metrics']['sharpe_ratio']}")
