"""
Alpaca Broker Client Connection Manager
Handles initialization and connection to Alpaca Broker API (multi-user).

Mirrors: app/brokers/alpaca/client.py
Key difference: Uses BrokerClient instead of TradingClient.
Also initializes market data clients (shared across all accounts).
"""

from alpaca.broker.client import BrokerClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class AlpacaBrokerClient:
    """Manages connection to Alpaca Broker API for multi-user brokerage."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        """
        Initialize the Alpaca Broker client.

        Args:
            api_key: Broker API key (defaults to env ALPACA_BROKER_API_KEY)
            secret_key: Broker secret key (defaults to env ALPACA_BROKER_SECRET_KEY)
            sandbox: Use sandbox (True) or production (False)
        """
        self.api_key = api_key or os.getenv("ALPACA_BROKER_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_BROKER_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Broker API credentials required. Provide via constructor or set "
                "ALPACA_BROKER_API_KEY and ALPACA_BROKER_SECRET_KEY environment variables."
            )

        self.sandbox = sandbox
        self.client = BrokerClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            sandbox=sandbox,
        )

        # Market data clients are shared — they don't need account_id.
        # Broker API credentials work for market data too.
        self.option_data_client = OptionHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
        )

    def get_client(self) -> BrokerClient:
        """Get the underlying BrokerClient instance."""
        return self.client

    def get_option_data_client(self) -> OptionHistoricalDataClient:
        """Get the option historical data client (shared, no account_id needed)."""
        return self.option_data_client

    def is_sandbox(self) -> bool:
        """Check if client is in sandbox mode."""
        return self.sandbox
