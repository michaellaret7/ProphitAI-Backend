from typing import Dict
from app.services.portfolio.portfolio import PortfolioService
from app.core.calculations.portfolio.concentration import PortfolioConcentration


class PortfolioConcentrationService:
    """
    Service to compute portfolio sector concentration.

    Wraps PortfolioConcentration calculation class and formats output
    for API responses with cleaned sector names.

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
        """
        Get sector concentration as percentage allocations.

        Returns:
            Dict mapping cleaned sector names to allocation percentages
        """
        return self._get_concentration('sector')

    def get_industry_concentration(self) -> Dict[str, float]:
        """
        Get industry concentration as percentage allocations.

        Returns:
            Dict mapping cleaned industry names to allocation percentages
        """
        return self._get_concentration('industry')

    def get_sub_industry_concentration(self) -> Dict[str, float]:
        """
        Get sub-industry concentration as percentage allocations.

        Returns:
            Dict mapping cleaned sub-industry names to allocation percentages
        """
        return self._get_concentration('sub_industry')

    def _get_concentration(self, level: str) -> Dict[str, float]:
        """
        Generic method to get concentration at any level (sector, industry, sub_industry).

        Args:
            level: One of 'sector', 'industry', or 'sub_industry'

        Returns:
            Dict mapping cleaned names to allocation percentages
        """
        # Get portfolio positions from database
        portfolio_service = PortfolioService()
        positions = portfolio_service.get_portfolio_positions(
            portfolio_id=self.portfolio_id,
            email=self.email
        )

        # Build portfolio_dict for concentration calculator
        portfolio_dict = {}
        for position in positions:
            ticker = position.get('ticker', '')
            allocation = float(position.get('allocation', 0.0))
            portfolio_dict[ticker] = {"allocation": allocation}

        # Calculate concentration at requested level
        concentration = PortfolioConcentration(portfolio_dict)

        if level == 'sector':
            data = concentration.sector_concentration()
            cleaned_data = self._clean_names(data, 'equity_sector_')
            # Add cash for sectors only
            total_allocated = sum(cleaned_data.values())
            if total_allocated < 100.0:
                cleaned_data['Cash'] = round(100.0 - total_allocated, 3)
        elif level == 'industry':
            data = concentration.industry_concentration()
            cleaned_data = self._clean_names(data, 'equity_industry_')
        elif level == 'sub_industry':
            data = concentration.sub_industry_concentration()
            cleaned_data = self._clean_names(data, 'equity_sub_industry_')
        else:
            raise ValueError(f"Invalid level: {level}")

        return cleaned_data

    def _clean_names(self, data: Dict[str, float], prefix: str) -> Dict[str, float]:
        """
        Clean names by removing prefixes and formatting.

        Args:
            data: Raw allocation dict from PortfolioConcentration
            prefix: Prefix to remove (e.g., 'equity_sector_')

        Returns:
            Dict with cleaned names and rounded values
        """
        cleaned = {}
        for name, value in data.items():
            # Remove prefix if present
            clean_name = name.replace(prefix, '')
            # Replace underscores with spaces and title case
            clean_name = clean_name.replace('_', ' ').title()
            # Values are stored as decimals in database (0.05 = 5%), multiply by 100
            cleaned[clean_name] = round(value * 100, 3)

        return cleaned

if __name__ == "__main__":
    portfolio_id = "4925a201-5f96-4ee6-9494-4a4d06599757"
    print(PortfolioConcentrationService(portfolio_id).get_sector_concentration())
    print(PortfolioConcentrationService(portfolio_id).get_industry_concentration())
    print(PortfolioConcentrationService(portfolio_id).get_sub_industry_concentration())