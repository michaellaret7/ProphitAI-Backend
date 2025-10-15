"""
Portfolio factor tilt calculation service.

Provides factor exposure analysis for portfolios considering position weights.
"""

from typing import Dict
from datetime import datetime, timedelta, timezone

from app.core.calculations.portfolio.factor_tilt import portfolio_factor_tilts


class PortfolioFactorTiltService:
    """
    Service for calculating portfolio-level factor tilts.

    Analyzes portfolio exposure to specific factors (value, growth, momentum,
    quality, volatility) considering position weights (long/short).
    """

    def __init__(
        self,
        weights: Dict[str, float],
        factor: str,
        years: int = 1,
    ):
        """
        Initialize portfolio factor tilt service.

        Args:
            weights: Dictionary of ticker -> allocation percentage (e.g., {"AAPL": 10.5, "MSFT": -5.0})
                    Positive values indicate long positions, negative indicate short positions.
            factor: Factor type - one of: value, growth, momentum, quality, volatility
            years: Number of years of historical data for price-based factors (default: 1)

        Raises:
            ValueError: If factor is invalid or weights is empty
        """
        if not weights:
            raise ValueError("weights cannot be empty")

        self.weights = weights
        self.factor = factor.lower()
        self.years = years

        # Validate factor type
        valid_factors = ["value", "growth", "momentum", "quality", "volatility"]
        if self.factor not in valid_factors:
            raise ValueError(f"Invalid factor: {self.factor}. Must be one of {valid_factors}")

    def calculate(self) -> Dict:
        """
        Calculate portfolio factor tilt.

        Returns:
            Dictionary with:
            - factor: Factor name
            - exposure_col: Name of the exposure column used
            - net_tilt: Net portfolio tilt (weighted average exposure)
            - long_tilt: Average exposure of long positions
            - short_tilt: Average exposure of short positions
            - per_ticker_exposure: Dictionary mapping ticker -> individual exposure
        """
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=self.years * 365)

        return portfolio_factor_tilts(
            weights=self.weights,
            factor=self.factor,
            start=start_dt,
            end=end_dt
        )
