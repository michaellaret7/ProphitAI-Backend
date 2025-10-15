"""
Alts domain services for alternative investment fund analytics.

Provides services for:
- Fund performance and position data
- Sector/industry/sub-industry concentration analysis
- Correlation matrix calculation
"""

from app.services.alts.alts import ProphitAltsServices
from app.services.alts.concentration import AltsConcentrationService
from app.services.alts.correlation import AltsCorrelationService

__all__ = [
    'ProphitAltsServices',
    'AltsConcentrationService',
    'AltsCorrelationService',
]
