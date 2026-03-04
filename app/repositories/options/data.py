"""Options data repository — contract discovery, chains, quotes, snapshots, bars.

Standalone repository that owns its own AlpacaClient and OptionsService instances.
"""

from typing import Dict, List, Optional, Tuple

from app.repositories.options.client import AlpacaClient
from app.repositories.options.service import OptionsService


# ════════════════════════════════════════════════════════════
# --> OptionsRepository
# ════════════════════════════════════════════════════════════

class OptionsRepository:
    """Self-contained options data repository with lazy-initialized Alpaca clients."""

    def __init__(self, feed: str = "indicative"):
        self._client = AlpacaClient()
        self._service = OptionsService(self._client, feed)

    # ---------------------------
    # Available Dates & Contracts
    # ---------------------------

    def get_available_dates(
        self,
        underlying: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        include_expired: bool = False,
        use_chain_fallback: bool = True,
    ) -> List[str]:
        """Return sorted list of unique expiration dates (YYYY-MM-DD) for the underlying."""
        return self._service.get_available_dates(
            underlying=underlying,
            start=start,
            end=end,
            include_expired=include_expired,
            use_chain_fallback=use_chain_fallback,
        )

    def get_available_contracts(
        self,
        underlying: str,
        expiration: Optional[str] = None,
        contract_type: Optional[str] = None,
        strike_range: Optional[Tuple[float, float]] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Discover available option contracts (OSI symbols)."""
        return self._service.get_available_contracts(
            underlying=underlying,
            expiration=expiration,
            contract_type=contract_type,
            strike_range=strike_range,
            status=status,
            limit=limit,
        )

    # ---------------------------
    # Chain, Bars, Quotes, Snapshots
    # ---------------------------

    def get_options_chain(
        self,
        underlying: str,
        expiration: Optional[str] = None,
        limit: Optional[int] = None,
        return_df: Optional[bool] = None,
        use_contract_join: bool = True,
    ):
        """Fetch options chain with quotes and greeks."""
        return self._service.get_options_chain(
            underlying=underlying,
            expiration=expiration,
            limit=limit,
            return_df=return_df,
            use_contract_join=use_contract_join,
        )

    def get_option_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Get OHLCV bars for an option contract."""
        return self._service.get_option_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
        )

    def get_option_latest_quote(self, symbol: str) -> Dict:
        """Get the latest bid/ask quote for an option contract (OSI symbol)."""
        return self._service.get_option_latest_quote(symbol=symbol)

    def get_option_snapshot(self, symbol: str) -> Dict:
        """Get a full snapshot (quote + trade + greeks) for an option contract."""
        return self._service.get_option_snapshot(symbol=symbol)


# ════════════════════════════════════════════════════════════
# --> Module-level singleton
# ════════════════════════════════════════════════════════════

_instance: Optional[OptionsRepository] = None


def get_options_repo() -> OptionsRepository:
    """Return a module-level singleton OptionsRepository."""
    global _instance
    if _instance is None:
        _instance = OptionsRepository()
    return _instance
