"""
Shared services used across multiple domains.

Provides services for:
- Stock price data fetching
"""

from app.services.shared.price import PriceService

__all__ = [
    'PriceService',
]
