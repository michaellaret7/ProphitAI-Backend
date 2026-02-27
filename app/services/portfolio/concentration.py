from typing import Dict
from app.services.portfolio.portfolio import PortfolioService
from app.core.calculations.portfolio_analytics.group_metrics import fetch_ticker_classifications


class PortfolioConcentrationService:
    """
    Service to compute portfolio sector concentration.

    Uses fetch_ticker_classifications to group allocations
    by sector, industry, or sub_industry.

    Args:
        portfolio_id: UUID of the portfolio
        email: Optional email for portfolio retrieval
    """

    def __init__(
        self,
        portfolio_id: str,
        email: str = "michaellaret7@gmail.com"
    ):
        self.portfolio_id = portfolio_id
        self.email = email

    def get_sector_concentration(self) -> Dict[str, float]:
        """Get sector concentration as percentage allocations."""
        return self._get_concentration('sector')

    def get_industry_concentration(self) -> Dict[str, float]:
        """Get industry concentration as percentage allocations."""
        return self._get_concentration('industry')

    def get_sub_industry_concentration(self) -> Dict[str, float]:
        """Get sub-industry concentration as percentage allocations."""
        return self._get_concentration('sub_industry')

    def _get_concentration(self, level: str) -> Dict[str, float]:
        """
        Get concentration at any level (sector, industry, sub_industry).

        Args:
            level: One of 'sector', 'industry', or 'sub_industry'

        Returns:
            Dict mapping cleaned names to allocation percentages
        """
        portfolio_service = PortfolioService()
        positions = portfolio_service.get_portfolio_positions(
            portfolio_id=self.portfolio_id,
            email=self.email
        )

        # Build ticker -> allocation mapping
        ticker_allocations = {}
        for position in positions:
            ticker = position.get('ticker', '')
            allocation = float(position.get('allocation', 0.0))
            if ticker:
                ticker_allocations[ticker] = allocation

        tickers = list(ticker_allocations.keys())
        if not tickers:
            return {}

        # Fetch classifications from DB
        classifications = fetch_ticker_classifications(tickers)

        # Group allocations by classification level
        grouped: Dict[str, float] = {}
        for ticker, allocation in ticker_allocations.items():
            classification = classifications.get(ticker, {})
            group_name = classification.get(level) or 'Unknown'
            grouped[group_name] = grouped.get(group_name, 0.0) + allocation

        # Clean names and convert to percentages
        prefix_map = {
            'sector': 'equity_sector_',
            'industry': 'equity_industry_',
            'sub_industry': 'equity_sub_industry_',
        }
        prefix = prefix_map.get(level, '')
        cleaned = self._clean_names(grouped, prefix)

        # Add cash for sectors only
        if level == 'sector':
            total_allocated = sum(cleaned.values())
            if total_allocated < 100.0:
                cleaned['Cash'] = round(100.0 - total_allocated, 3)

        return cleaned

    def _clean_names(self, data: Dict[str, float], prefix: str) -> Dict[str, float]:
        """
        Clean names by removing prefixes and formatting.

        Args:
            data: Raw allocation dict
            prefix: Prefix to remove (e.g., 'equity_sector_')

        Returns:
            Dict with cleaned names and rounded percentage values
        """
        cleaned = {}
        for name, value in data.items():
            clean_name = name.replace(prefix, '')
            clean_name = clean_name.replace('_', ' ').title()
            cleaned[clean_name] = round(value * 100, 3)
        return cleaned
