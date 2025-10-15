from typing import Dict, Any
from app.services.portfolio.returns import PortfolioReturnsService
from app.services.portfolio.portfolio import PortfolioService
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

class PortfolioMetricsService:
    """
    Service to compute all portfolio metrics for dashboard cards and tooltips.

    Follows the precomputation pattern from PortfolioReturnsService.
    Leverages existing calculation services to avoid code duplication (DRY).

    Precomputed attributes:
    - risk_metrics: Annualized return, volatility, max drawdown, Sharpe ratio, VaR
    - asset_allocation: Breakdown by sector
    - top_performers: Top 2 performing tickers
    - worst_performers: Worst 2 performing tickers

    Args:
        portfolio_id: UUID of the portfolio
        years: Historical data window (default 2)
        email: Optional email for portfolio retrieval
    """

    def __init__(
        self,
        portfolio_id: str,
        years: int = 2,
        email: str = "michaellaret7@gmail.com"
    ):
        self.portfolio_id = portfolio_id
        self.years = years
        self.email = email

        # Initialize state
        self.risk_metrics: Dict[str, float] = {}
        self.asset_allocation: Dict[str, float] = {}
        self.top_performers: list = []
        self.worst_performers: list = []

        # Precompute all metrics
        self._calculate_metrics()

    def _calculate_metrics(self):
        """
        Calculate all metrics using existing services.

        Leverages PortfolioReturnsService which already computes:
        - Sharpe ratio
        - Volatility
        - Max drawdown
        - VaR (via daily returns)
        """
        # Reuse PortfolioReturnsService for risk metrics
        returns_service = PortfolioReturnsService(
            portfolio_id=self.portfolio_id,
            years=self.years,
            email=self.email
        )

        # Get summary metrics (already includes sharpe, vol, max_dd)
        summary = returns_service.get_summary_metrics()

        # Calculate VaR (95% confidence) from daily returns
        if not returns_service.daily_returns.empty:
            var_95_pct = returns_service.daily_returns.quantile(0.05)
            var_95_dollar = var_95_pct * returns_service.initial_nav
        else:
            var_95_dollar = 0.0

        # Build risk metrics response
        self.risk_metrics = {
            "annualized_return": summary.get('annualized_return', 0.0),
            "annualized_volatility": summary.get('volatility', 0.0),
            "max_drawdown": summary.get('max_drawdown', 0.0),
            "sharpe_ratio": summary.get('sharpe_ratio', 0.0),
            "var_95": round(var_95_dollar, 0)
        }

        # Calculate asset allocation
        portfolio_service = PortfolioService()
        positions = portfolio_service.get_portfolio_positions(
            portfolio_id=self.portfolio_id,
            email=self.email
        )

        self.asset_allocation = self._calculate_asset_allocation(positions)

        # Calculate top and worst performers
        ticker_performance = self._calculate_ticker_performance(returns_service)
        self.top_performers = ticker_performance['top']
        self.worst_performers = ticker_performance['worst']

    def _calculate_asset_allocation(self, positions) -> Dict[str, float]:
        """
        Group positions by sector from database.

        Args:
            positions: List of position dicts with ticker, allocation

        Returns:
            Dict mapping sector names to total allocation percentage
        """
        allocation = {}

        for position in positions:
            ticker = position.get('ticker', '')
            alloc = float(position.get('allocation', 0.0))

            # Fetch sector from database
            with MarketSession() as session:
                ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker).first()
                sector = ticker_obj.sector if ticker_obj and ticker_obj.sector else 'Other'

            # Add allocation to sector
            if sector in allocation:
                allocation[sector] += alloc
            else:
                allocation[sector] = alloc

        # Calculate total allocated and assign remainder to cash
        total_allocated = sum(allocation.values())
        if total_allocated < 100.0:
            allocation['Cash'] = round(100.0 - total_allocated, 1)

        # Clean up sector names: remove prefix, capitalize, remove underscores
        cleaned_allocation = {}
        for sector, value in allocation.items():
            # Remove 'equity_sector_' prefix if present
            clean_sector = sector.replace('equity_sector_', '')
            # Replace underscores with spaces and title case
            clean_sector = clean_sector.replace('_', ' ').title()
            cleaned_allocation[clean_sector] = round(value, 1)

        return cleaned_allocation

    def _calculate_ticker_performance(self, returns_service: PortfolioReturnsService) -> Dict[str, list]:
        """
        Calculate top 2 and worst 2 performing tickers based on total return.

        Args:
            returns_service: PortfolioReturnsService instance with price data

        Returns:
            Dict with 'top' and 'worst' lists containing ticker performance data
        """
        ticker_returns = {}

        # Calculate total return for each ticker over the period
        for ticker, prices in returns_service.price_data.items():
            if len(prices) > 0:
                total_return = ((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]) * 100
                ticker_returns[ticker] = total_return

        # Sort by return
        sorted_tickers = sorted(ticker_returns.items(), key=lambda x: x[1], reverse=True)

        # Get top 2 and worst 2
        top_2 = [{"ticker": t[0], "return": round(t[1], 2)} for t in sorted_tickers[:2]]
        worst_2 = [{"ticker": t[0], "return": round(t[1], 2)} for t in sorted_tickers[-2:]]

        return {
            "top": top_2,
            "worst": worst_2
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics for API response.

        Returns:
            Dict with risk_metrics, asset_allocation, top_performers, worst_performers
        """
        return {
            "risk_metrics": self.risk_metrics,
            "asset_allocation": self.asset_allocation,
            "top_performers": self.top_performers,
            "worst_performers": self.worst_performers
        }
