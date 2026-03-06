"""
Services layer for ProphitAI.

Domain-organized service modules:
- broker: SnapTrade brokerage operations (onboarding, account, trading, proposals)
- portfolio: Portfolio management and analytics
- shared: Cross-domain utility services
"""

# Export all services at the root level for convenience
from app.services.portfolio import (
    PortfolioService,
    PortfolioReturnsService,
    PortfolioMetricsService,
    PortfolioConcentrationService,
    PortfolioPerformanceComparisonService,
)
from app.services.shared import (
    PriceService,
)

__all__ = [
    # Portfolio services
    'PortfolioService',
    'PortfolioReturnsService',
    'PortfolioMetricsService',
    'PortfolioConcentrationService',
    'PortfolioPerformanceComparisonService',
    # Shared services
    'PriceService',
]
