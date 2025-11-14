"""
Services layer for ProphitAI.

Domain-organized service modules:
- alts: Alternative investment fund analytics
- portfolio: Portfolio management and analytics
- shared: Cross-domain utility services
"""

# Export all services at the root level for convenience
from app.services.alts import (
    ProphitAltsServices,
    AltsConcentrationService,
    AltsCorrelationService,
)
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
    # Alts services
    'ProphitAltsServices',
    'AltsConcentrationService',
    'AltsCorrelationService',
    # Portfolio services
    'PortfolioService',
    'PortfolioReturnsService',
    'PortfolioMetricsService',
    'PortfolioConcentrationService',
    'PortfolioPerformanceComparisonService',
    # Shared services
    'PriceService',
]
