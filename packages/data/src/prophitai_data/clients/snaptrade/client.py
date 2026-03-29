"""
SnapTrade Client Connection Manager
Handles SDK initialization and credential loading.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from snaptrade_client import SnapTrade

load_dotenv()


class SnapTradeClient:
    """Manages connection to SnapTrade API."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        consumer_key: Optional[str] = None,
    ):
        """
        Initialize the SnapTrade client.

        Args:
            client_id: Partner client ID (defaults to env SNAPTRADE_CLIENT_ID)
            consumer_key: Partner consumer key (defaults to env SNAPTRADE_CONSUMER_KEY)
        """
        self.client_id = client_id or os.getenv("SNAPTRADE_CLIENT_ID")
        self.consumer_key = consumer_key or os.getenv("SNAPTRADE_CONSUMER_KEY")

        if not self.client_id or not self.consumer_key:
            raise ValueError(
                "SnapTrade credentials required. Provide via constructor or set "
                "SNAPTRADE_CLIENT_ID and SNAPTRADE_CONSUMER_KEY environment variables."
            )

        self.client = SnapTrade(
            client_id=self.client_id,
            consumer_key=self.consumer_key,
        )

    def get_client(self) -> SnapTrade:
        """Get the underlying SnapTrade SDK instance."""
        return self.client

    def get_client_id(self) -> str:
        """Get the partner client ID."""
        assert self.client_id is not None
        return self.client_id
