"""
SnapTrade Connections Service
Manages brokerage authorization connections (link/refresh/disable/remove).
"""

from typing import Any, Dict, List

from snaptrade_client import SnapTrade

from prophitai_data.clients.snaptrade.utils import extract_body


class SnapTradeConnections:
    """Brokerage connection management for SnapTrade."""

    def __init__(self, client: SnapTrade):
        self._conn = client.connections

    def list_authorizations(
        self, user_id: str, user_secret: str,
    ) -> List[Dict[str, Any]]:
        """
        List all brokerage authorizations for a user.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
        """
        response = self._conn.list_brokerage_authorizations(
            user_id=user_id, user_secret=user_secret,
        )
        return extract_body(response)

    def get_authorization(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> Dict[str, Any]:
        """
        Get details for a specific brokerage authorization.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            authorization_id: Authorization ID
        """
        response = self._conn.detail_brokerage_authorization(
            user_id=user_id,
            user_secret=user_secret,
            authorization_id=authorization_id,
        )
        return extract_body(response)

    def refresh_authorization(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> Dict[str, Any]:
        """
        Refresh a brokerage authorization to sync latest data.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            authorization_id: Authorization ID
        """
        response = self._conn.refresh_brokerage_authorization(
            user_id=user_id,
            user_secret=user_secret,
            authorization_id=authorization_id,
        )
        return extract_body(response)

    def disable_authorization(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> Dict[str, Any]:
        """
        Disable a brokerage authorization (stops syncing).

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            authorization_id: Authorization ID
        """
        response = self._conn.disable_brokerage_authorization(
            user_id=user_id,
            user_secret=user_secret,
            authorization_id=authorization_id,
        )
        return extract_body(response)

    def remove_authorization(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> None:
        """
        Permanently remove a brokerage authorization.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            authorization_id: Authorization ID
        """
        self._conn.remove_brokerage_authorization(
            user_id=user_id,
            user_secret=user_secret,
            authorization_id=authorization_id,
        )
