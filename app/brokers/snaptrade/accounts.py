"""
SnapTrade Account Information Service
Handles account queries, balances, holdings, positions, and orders.
"""

from typing import Any, Dict, List, Optional

from snaptrade_client import SnapTrade

from app.brokers.snaptrade.models.holdings import Holdings
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

    def get_holdings(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> Holdings:
        """
        Get full holdings for an account (positions + balances + orders + options).

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID

        Returns:
            Holdings model with positions, orders, option_positions, and total_value
        """
        response = self._accounts.get_user_holdings(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
        )
        raw = extract_body(response)
        return Holdings.from_raw(raw)

    def get_all_holdings(
        self, user_id: str, user_secret: str,
    ) -> List[Dict[str, Any]]:
        """
        Get holdings across all accounts for a user.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
        """
        response = self._accounts.get_all_user_holdings(
            user_id=user_id, user_secret=user_secret,
        )
        return extract_body(response)

    def get_orders(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        state: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get orders for an account.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            state: Filter by state ('all', 'open', 'executed')
            days: Number of days to look back
        """
        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
        }
        if state is not None:
            kwargs["state"] = state
        if days is not None:
            kwargs["days"] = days

        response = self._accounts.get_user_account_orders(**kwargs)
        return extract_body(response)

    def get_activities(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get account activities (fills, dividends, transfers, etc.).

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            type: Activity type filter
        """
        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
        }
        if start_date is not None:
            kwargs["start_date"] = start_date
        if end_date is not None:
            kwargs["end_date"] = end_date
        if type is not None:
            kwargs["type"] = type

        response = self._accounts.get_account_activities(**kwargs)
        return extract_body(response)
