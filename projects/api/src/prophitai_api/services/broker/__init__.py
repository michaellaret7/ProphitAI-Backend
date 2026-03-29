"""Broker services package — re-exports all public broker service functions and classes."""

from .account import (
    get_broker_account,
    get_balances,
    get_equity,
    get_buying_power,
    get_cash_balance,
)
from .connections import (
    list_connections,
    remove_connection,
)
from .onboarding import (
    register_snaptrade_user,
    save_snaptrade_account,
    get_snaptrade_connect_url,
)
from .proposals import approve_proposal
from .trading import (
    buy,
    sell,
    get_orders,
    get_activities,
    cancel_order,
    get_positions,
    get_position,
    close_position,
    get_portfolio_performance,
    get_portfolio_history,
)

__all__ = [
    # account
    "get_broker_account",
    "get_balances",
    "get_equity",
    "get_buying_power",
    "get_cash_balance",
    # connections
    "list_connections",
    "remove_connection",
    # onboarding
    "register_snaptrade_user",
    "save_snaptrade_account",
    "get_snaptrade_connect_url",
    # proposals
    "approve_proposal",
    # trading
    "buy",
    "sell",
    "get_orders",
    "get_activities",
    "cancel_order",
    "get_positions",
    "get_position",
    "close_position",
    "get_portfolio_performance",
    "get_portfolio_history",
]
