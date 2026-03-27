"""
SnapTrade Broker Module
Brokerage aggregation layer via SnapTrade -- equities and options execution,
account management, and reporting. Options data sourced from Alpaca.
"""

from prophitai_data.clients.snaptrade.broker import SnapTradeBroker
from prophitai_data.clients.snaptrade.client import SnapTradeClient
from prophitai_data.clients.snaptrade.credentials import (
    get_snaptrade_broker,
    resolve_snaptrade_credentials,
    resolve_broker_account,
)

__all__ = [
    "SnapTradeBroker",
    "SnapTradeClient",
    "get_snaptrade_broker",
    "resolve_snaptrade_credentials",
    "resolve_broker_account",
]
