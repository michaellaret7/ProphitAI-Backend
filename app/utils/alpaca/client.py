"""
Alpaca Client Connection Manager
Handles initialization and connection to Alpaca Trading API
"""

from alpaca.trading.client import TradingClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class AlpacaClient:
    """Manages connection to Alpaca Trading API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True
    ):
        """
        Initialize the Alpaca client connection

        Args:
            api_key: Alpaca API key (defaults to env variable ALPACA_API_KEY)
            secret_key: Alpaca secret key (defaults to env variable ALPACA_SECRET_KEY)
            paper: Use paper trading (True) or live trading (False)
        """
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY')

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "API credentials required. Provide via constructor or set "
                "ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )

        self.paper = paper
        self.client = TradingClient(self.api_key, self.secret_key, paper=paper)

    def get_client(self) -> TradingClient:
        """Get the underlying TradingClient instance"""
        return self.client

    def is_paper_trading(self) -> bool:
        """Check if client is in paper trading mode"""
        return self.paper
