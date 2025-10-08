from typing import Dict, Any
from app.services.portfolio_returns import PortfolioReturnsService
from app.services.portfolio import PortfolioService


class PortfolioMetricsService:
    """
    Service to compute all portfolio metrics for dashboard cards and tooltips.

    Follows the precomputation pattern from PortfolioReturnsService.
    Leverages existing calculation services to avoid code duplication (DRY).

    Precomputed attributes:
    - risk_metrics: Volatility, max drawdown, Sharpe ratio, VaR
    - asset_allocation: Breakdown by asset class
    - risk_exposure: Categorical risk levels

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
        self.risk_exposure: Dict[str, str] = {}

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
            "volatility": summary.get('volatility', 0.0),
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
        self.risk_exposure = self._assess_risk_exposure(
            volatility=summary.get('volatility', 0.0),
            max_drawdown=summary.get('max_drawdown', 0.0),
            positions=positions
        )

    def _calculate_asset_allocation(self, positions) -> Dict[str, float]:
        """
        Group positions by asset class/sector.

        Args:
            positions: List of position dicts with ticker, allocation, sector

        Returns:
            Dict mapping asset class to total allocation percentage
        """
        allocation = {
            "equities": 0.0,
            "etfs": 0.0,
            "fixed_income": 0.0,
            "commodities": 0.0,
            "alternatives": 0.0,
            "cash": 0.0
        }

        for position in positions:
            ticker = position.get('ticker', '')
            alloc = float(position.get('allocation', 0.0))  # Convert to float

            # Simple heuristic: classify by ticker patterns
            # TODO: Replace with proper asset class field from DB
            if any(bond in ticker.upper() for bond in ['TLT', 'IEF', 'SHY', 'BND', 'AGG']):
                allocation['fixed_income'] += alloc
            elif any(etf in ticker.upper() for etf in ['SPY', 'QQQ', 'IWM', 'VTI', 'VOO']):
                allocation['etfs'] += alloc
            elif any(comm in ticker.upper() for comm in ['GLD', 'SLV', 'USO', 'DBC']):
                allocation['commodities'] += alloc
            elif ticker.upper() in ['BIL', 'SGOV']:
                allocation['cash'] += alloc
            else:
                allocation['equities'] += alloc

        return {k: round(v, 1) for k, v in allocation.items()}

    def _assess_risk_exposure(
        self,
        volatility: float,
        max_drawdown: float,
        positions
    ) -> Dict[str, str]:
        """
        Determine categorical risk levels.

        Args:
            volatility: Annualized volatility (%)
            max_drawdown: Max drawdown (%)
            positions: List of positions

        Returns:
            Dict mapping risk type to level ('low', 'medium', 'high')
        """
        # Market risk based on volatility
        if volatility > 20:
            market_risk = "high"
        elif volatility > 12:
            market_risk = "medium"
        else:
            market_risk = "low"

        # Credit risk based on fixed income allocation
        # TODO: Enhance with credit ratings when available
        credit_risk = "medium"

        # Liquidity risk based on position concentration
        num_positions = len(positions)
        if num_positions < 5:
            liquidity_risk = "high"
        elif num_positions < 15:
            liquidity_risk = "medium"
        else:
            liquidity_risk = "low"

        # Currency risk - placeholder
        # TODO: Implement based on international exposure
        currency_risk = "low"

        return {
            "market_risk": market_risk,
            "credit_risk": credit_risk,
            "liquidity_risk": liquidity_risk,
            "currency_risk": currency_risk
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics for API response.

        Returns:
            Dict with risk_metrics, asset_allocation, risk_exposure
        """
        return {
            "risk_metrics": self.risk_metrics,
            "asset_allocation": self.asset_allocation,
            "risk_exposure": self.risk_exposure
        }
