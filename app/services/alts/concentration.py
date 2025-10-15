from typing import Dict
from app.repositories.prophit_alts_data import get_fund_final_positions
from app.core.calculations.portfolio.concentration import PortfolioConcentration


class AltsConcentrationService:
    """
    Service to compute alts fund concentration across sectors, industries, and sub-industries.

    Wraps PortfolioConcentration calculation class and formats output
    for API responses with cleaned names.

    Args:
        fund_name: Name of the fund (e.g., "consumer_staples_fund")
    """

    def __init__(self, fund_name: str):
        self.fund_name = fund_name

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

    def get_industry_concentration_with_positions(self) -> Dict[str, Dict[str, float]]:
        """
        Get industry concentration with long/short breakdown.

        Returns:
            Dict mapping industry names to {'total': %, 'long': %, 'short': %}
        """
        return self._get_concentration_with_positions('industry')

    def get_sub_industry_concentration_with_positions(self) -> Dict[str, Dict[str, float]]:
        """
        Get sub-industry concentration with long/short breakdown.

        Returns:
            Dict mapping sub-industry names to {'total': %, 'long': %, 'short': %}
        """
        return self._get_concentration_with_positions('sub_industry')

    def _get_concentration(self, level: str) -> Dict[str, float]:
        """
        Generic method to get concentration at any level (sector, industry, sub_industry).

        Args:
            level: One of 'sector', 'industry', or 'sub_industry'

        Returns:
            Dict mapping cleaned names to allocation percentages
        """
        # Get fund positions from database
        positions = get_fund_final_positions(fund_name=self.fund_name)

        if not positions:
            raise ValueError(f"No positions found for fund: {self.fund_name}")

        # Build portfolio_dict for concentration calculator
        portfolio_dict = {}
        for position in positions:
            ticker = position.get('ticker_name', '')
            allocation = float(position.get('portfolio_allocation', 0.0))
            position_type = position.get('position', 'LONG')

            # Handle position type (LONG/SHORT)
            if 'SHORT' in str(position_type).upper():
                portfolio_dict[ticker] = {"allocation": allocation, "position": "short"}
            else:
                portfolio_dict[ticker] = {"allocation": allocation, "position": "long"}

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

    def _get_concentration_with_positions(self, level: str) -> Dict[str, Dict[str, float]]:
        """
        Calculate concentration with long/short breakdown.

        Args:
            level: One of 'industry' or 'sub_industry'

        Returns:
            Dict mapping names to {'total': %, 'long': %, 'short': %, 'net': %}
        """
        # Get fund positions from database
        positions = get_fund_final_positions(fund_name=self.fund_name)

        if not positions:
            raise ValueError(f"No positions found for fund: {self.fund_name}")

        # Get ticker metadata to map tickers to industries
        from app.db.core.db_config import MarketSession
        from app.db.core.models.market_data_models import Ticker

        tickers = [p.get('ticker_name') for p in positions]
        session = MarketSession()
        try:
            ticker_rows = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
        finally:
            session.close()

        # Build mapping from ticker to industry/sub_industry
        ticker_to_category = {}
        for row in ticker_rows:
            if level == 'industry':
                category = getattr(row, 'industry', 'Unknown')
            else:  # sub_industry
                category = getattr(row, 'sub_industry', 'Unknown')
            ticker_to_category[row.ticker] = category

        # Calculate long/short totals per category
        category_breakdown = {}
        for position in positions:
            ticker = position.get('ticker_name', '')
            allocation = float(position.get('portfolio_allocation', 0.0))
            position_type = position.get('position', 'LONG')

            category = ticker_to_category.get(ticker, 'Unknown')

            if category not in category_breakdown:
                category_breakdown[category] = {'long': 0.0, 'short': 0.0}

            # Determine if long or short
            if 'SHORT' in str(position_type).upper():
                category_breakdown[category]['short'] += allocation
            else:
                category_breakdown[category]['long'] += allocation

        # Clean names and calculate totals/net
        cleaned_breakdown = {}
        for category, values in category_breakdown.items():
            # Remove prefix and format name
            if level == 'industry':
                clean_name = category.replace('equity_industry_', '')
            else:
                clean_name = category.replace('equity_sub_industry_', '')
            clean_name = clean_name.replace('_', ' ').title()

            # Convert to percentages and calculate net
            long_pct = round(values['long'] * 100, 3)
            short_pct = round(values['short'] * 100, 3)
            total_pct = round((values['long'] + values['short']) * 100, 3)
            net_pct = round((values['long'] - values['short']) * 100, 3)

            cleaned_breakdown[clean_name] = {
                'total': total_pct,
                'long': long_pct,
                'short': short_pct,
                'net': net_pct
            }

        return cleaned_breakdown

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
    fund_name = "consumer_staples_fund"
    service = AltsConcentrationService(fund_name)
    print("Sectors:", service.get_sector_concentration())
    print("Industries:", service.get_industry_concentration())
    print("Sub-Industries:", service.get_sub_industry_concentration())
