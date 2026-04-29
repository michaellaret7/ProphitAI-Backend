"""Alpaca trading client connection manager.

Wraps the Alpaca SDK ``TradingClient`` and resolves credentials from
constructor arguments or environment variables. ``.env`` is loaded
lazily on instantiation rather than at import so importing the module
is side-effect-free.
"""

from __future__ import annotations

import os

from alpaca.trading.client import TradingClient
from dotenv import load_dotenv


class AlpacaClient:
    """Manages connection to the Alpaca Trading API.

    Args:
        api_key: Alpaca API key. Falls back to ``ALPACA_API_KEY`` env var.
        secret_key: Alpaca secret key. Falls back to ``ALPACA_SECRET_KEY``.
        paper: Paper-trading mode when ``True`` (default), else live.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
    ):
        load_dotenv()

        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "API credentials required. Provide via constructor or set "
                "ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
            )

        self.paper = paper
        self.client = TradingClient(self.api_key, self.secret_key, paper=paper)

    def get_client(self) -> TradingClient:
        return self.client

    def is_paper_trading(self) -> bool:
        return self.paper
