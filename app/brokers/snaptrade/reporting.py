"""
SnapTrade Reporting Service
Handles performance reports.
"""

from typing import Any, Dict, Optional

from snaptrade_client import SnapTrade

from app.brokers.snaptrade.utils import extract_body


class SnapTradeReporting:
    """Transaction history and performance reporting for SnapTrade."""

    def __init__(self, client: SnapTrade):
        self._reporting = client.transactions_and_reporting

    def get_performance_report(
        self,
        user_id: str,
        user_secret: str,
        start_date: str,
        end_date: str,
        accounts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get portfolio performance report for a date range.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            accounts: Comma-separated account IDs to filter
        """
        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "start_date": start_date,
            "end_date": end_date,
        }
        if accounts is not None:
            kwargs["accounts"] = accounts

        response = self._reporting.get_reporting_custom_range(**kwargs)
        return extract_body(response)
