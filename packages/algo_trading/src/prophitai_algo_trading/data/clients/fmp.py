"""Unified FMP API client composed from domain-specific mixins."""

from prophitai_algo_trading.data.clients.base import FMPBaseClient
from prophitai_algo_trading.data.clients.fmp_prices import FMPPricesMixin


class FmpClient(
    FMPBaseClient,
    FMPPricesMixin,
):
    """Unified FMP API client."""
    pass
