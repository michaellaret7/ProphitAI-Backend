"""
Alpaca Broker Client Connection Manager
Handles initialization and connection to Alpaca Broker API (multi-user).

Mirrors: app/brokers/alpaca/client.py
Key difference: Uses BrokerClient instead of TradingClient.

Market data (options chains, quotes, bars) uses Trading API keys because
the Broker sandbox lacks OPRA data entitlements. Order execution still
routes through the BrokerClient.
"""

from alpaca.broker.client import BrokerClient
from alpaca.trading.client import TradingClient
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

        # Reason: Broker sandbox accounts lack OPRA data agreements, so options
        # market data and contract discovery must go through Trading API keys
        # which hit data.alpaca.markets with full options support.
        trading_api_key = os.getenv("ALPACA_API_KEY")
        trading_secret_key = os.getenv("ALPACA_SECRET_KEY")

        if not trading_api_key or not trading_secret_key:
            raise ValueError(
                "Trading API credentials required for options market data. Set "
                "ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )

        self.trading_client = TradingClient(
            api_key=trading_api_key,
            secret_key=trading_secret_key,
            paper=sandbox,
        )

        self.option_data_client = OptionHistoricalDataClient(
            api_key=trading_api_key,
            secret_key=trading_secret_key,
        )

    def get_client(self) -> BrokerClient:
        """Get the underlying BrokerClient instance."""
        return self.client

    def get_trading_client(self) -> TradingClient:
        """Get the TradingClient used for contract discovery and options data."""
        return self.trading_client

    def get_option_data_client(self) -> OptionHistoricalDataClient:
        """Get the option historical data client (uses Trading API keys)."""
        return self.option_data_client

    def is_sandbox(self) -> bool:
        """Check if client is in sandbox mode."""
        return self.sandbox
