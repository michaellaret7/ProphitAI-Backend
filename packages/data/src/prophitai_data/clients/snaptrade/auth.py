"""
SnapTrade Authentication Service
Handles user registration, login, deletion, and secret management.
"""

from typing import Any, Dict, List, Optional

from snaptrade_client import SnapTrade

from prophitai_data.clients.snaptrade.utils import extract_body


class SnapTradeAuth:
    """User lifecycle management for SnapTrade."""

    def __init__(self, client: SnapTrade):
        self._auth = client.authentication

    def register_user(self, user_id: str) -> Dict[str, Any]:
        """
        Register a new user with SnapTrade.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Dict with 'userId' and 'userSecret'
        """
        response = self._auth.register_snap_trade_user(user_id=user_id)
        return extract_body(response)

    def login_user(
        self,
        user_id: str,
        user_secret: str,
        broker: Optional[str] = None,
        connection_type: Optional[str] = "trade",
        custom_redirect: Optional[str] = None,
        reconnect: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a login redirect URL for the SnapTrade connection portal.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            broker: Pre-select a specific brokerage
            connection_type: Filter connection type ('read', 'trade')
            custom_redirect: URL to redirect after connection
            reconnect: Authorization ID to reconnect

        Returns:
            Dict with 'redirectURI'
        """
        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
        }
        if broker is not None:
            kwargs["broker"] = broker
        if connection_type is not None:
            kwargs["connection_type"] = connection_type
        if custom_redirect is not None:
            kwargs["custom_redirect"] = custom_redirect
        if reconnect is not None:
            kwargs["reconnect"] = reconnect

        response = self._auth.login_snap_trade_user(**kwargs)
        return extract_body(response)

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user and all associated data from SnapTrade.

        Args:
            user_id: SnapTrade user ID to delete
        """
        response = self._auth.delete_snap_trade_user(user_id=user_id)
        return extract_body(response)

    def list_users(self) -> List[str]:
        """List all registered SnapTrade user IDs."""
        response = self._auth.list_snap_trade_users()
        return extract_body(response)

    def reset_user_secret(self, user_id: str, user_secret: str) -> Dict[str, Any]:
        """
        Reset a user's secret key.

        Args:
            user_id: SnapTrade user ID
            user_secret: Current user secret

        Returns:
            Dict with 'userId' and new 'userSecret'
        """
        response = self._auth.reset_snap_trade_user_secret(
            user_id=user_id,
            user_secret=user_secret,
        )
        return extract_body(response)
