"""
SnapTrade Account Information Service
Handles account queries, balances, and holdings.
"""

from typing import Any, Dict, List

from snaptrade_client import SnapTrade

from app.brokers.snaptrade.utils import extract_body


class SnapTradeAccounts:
    """Account information and queries for SnapTrade-connected brokerages."""

    def __init__(self, client: SnapTrade):
        self._accounts = client.account_information

    def list_accounts(self, user_id: str, user_secret: str) -> List[Dict[str, Any]]:
        """
        List all brokerage accounts linked to a user.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret

        Returns:
            List of account dicts
        """
        response = self._accounts.list_user_accounts(
            user_id=user_id, user_secret=user_secret,
        )
        return extract_body(response)

    def get_account_details(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed info for a specific account.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
        """
        response = self._accounts.get_user_account_details(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
        )
        return extract_body(response)

    def get_balances(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get cash balances for an account.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
        """
        response = self._accounts.get_user_account_balance(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
        )
        return extract_body(response)

