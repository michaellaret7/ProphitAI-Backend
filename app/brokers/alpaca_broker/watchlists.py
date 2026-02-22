"""
Alpaca Broker Watchlist Management
Full CRUD for per-account watchlists via the Broker API SDK.

NEW — no equivalent in Trading API (Trading API watchlists are for your own account only).
"""

from alpaca.broker.client import BrokerClient
from alpaca.trading.requests import (
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
)
from typing import Optional, List, Dict


class BrokerWatchlists:
    """Handles watchlist CRUD for end user accounts."""

    def __init__(self, client: BrokerClient):
        self.client = client

    # ════════════════════════════════════════════════════════════
    # --> Helper funcs
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _format_watchlist(wl) -> Dict:
        """Format a watchlist model into a standardized dict."""
        assets = getattr(wl, "assets", None) or []
        return {
            "watchlist_id": str(wl.id),
            "name": wl.name,
            "account_id": str(getattr(wl, "account_id", None)),
            "symbols": [getattr(a, "symbol", str(a)) for a in assets],
            "created_at": str(wl.created_at) if getattr(wl, "created_at", None) else None,
            "updated_at": str(wl.updated_at) if getattr(wl, "updated_at", None) else None,
        }

    # ════════════════════════════════════════════════════════════
    # Watchlist CRUD
    # ════════════════════════════════════════════════════════════

    def create_watchlist(
        self,
        account_id: str,
        name: str,
        symbols: Optional[List[str]] = None,
    ) -> Dict:
        """
        Create a new watchlist for an account.

        Args:
            account_id: User's Alpaca account ID
            name: Watchlist name
            symbols: Initial list of ticker symbols to include
        """
        try:
            request = CreateWatchlistRequest(name=name, symbols=symbols or [])
            wl = self.client.create_watchlist_for_account(
                account_id=account_id,
                watchlist_data=request,
            )
            return self._format_watchlist(wl)
        except Exception as e:
            raise Exception(f"Failed to create watchlist for {account_id}: {str(e)}")

    def get_watchlists(self, account_id: str) -> List[Dict]:
        """Get all watchlists for an account."""
        try:
            watchlists = self.client.get_watchlists_for_account(account_id=account_id)
            return [self._format_watchlist(wl) for wl in watchlists]
        except Exception as e:
            raise Exception(f"Failed to get watchlists for {account_id}: {str(e)}")

    def get_watchlist(self, account_id: str, watchlist_id: str) -> Dict:
        """Get a specific watchlist by ID."""
        try:
            wl = self.client.get_watchlist_for_account_by_id(
                account_id=account_id,
                watchlist_id=watchlist_id,
            )
            return self._format_watchlist(wl)
        except Exception as e:
            raise Exception(f"Failed to get watchlist {watchlist_id}: {str(e)}")

    def update_watchlist(
        self,
        account_id: str,
        watchlist_id: str,
        name: Optional[str] = None,
        symbols: Optional[List[str]] = None,
    ) -> Dict:
        """
        Update a watchlist (replace name and/or symbols).

        Args:
            account_id: User's Alpaca account ID
            watchlist_id: Watchlist UUID
            name: New name (optional)
            symbols: New full list of symbols (replaces existing)
        """
        try:
            request = UpdateWatchlistRequest(name=name, symbols=symbols)
            wl = self.client.update_watchlist_for_account_by_id(
                account_id=account_id,
                watchlist_id=watchlist_id,
                watchlist_data=request,
            )
            return self._format_watchlist(wl)
        except Exception as e:
            raise Exception(f"Failed to update watchlist {watchlist_id}: {str(e)}")

    def add_symbol(self, account_id: str, watchlist_id: str, symbol: str) -> Dict:
        """Add a single symbol to a watchlist."""
        try:
            wl = self.client.add_asset_to_watchlist_for_account_by_id(
                account_id=account_id,
                watchlist_id=watchlist_id,
                symbol=symbol,
            )
            return self._format_watchlist(wl)
        except Exception as e:
            raise Exception(f"Failed to add {symbol} to watchlist {watchlist_id}: {str(e)}")

    def remove_symbol(self, account_id: str, watchlist_id: str, symbol: str) -> Dict:
        """Remove a single symbol from a watchlist."""
        try:
            wl = self.client.remove_asset_from_watchlist_for_account_by_id(
                account_id=account_id,
                watchlist_id=watchlist_id,
                symbol=symbol,
            )
            return self._format_watchlist(wl)
        except Exception as e:
            raise Exception(f"Failed to remove {symbol} from watchlist {watchlist_id}: {str(e)}")

    def delete_watchlist(self, account_id: str, watchlist_id: str) -> None:
        """Delete a watchlist."""
        try:
            self.client.delete_watchlist_from_account_by_id(
                account_id=account_id,
                watchlist_id=watchlist_id,
            )
        except Exception as e:
            raise Exception(f"Failed to delete watchlist {watchlist_id}: {str(e)}")
