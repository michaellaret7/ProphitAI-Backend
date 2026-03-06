"""Broker controller functions — account, trading, and portfolio history."""

from .account import (
    get_broker_account_controller,
    get_balances_controller,
    get_account_activities_controller,
    get_connection_status_controller,
    snaptrade_register_controller,
    snaptrade_callback_controller,
    snaptrade_connect_controller,
)
from .trading import (
    buy_controller,
    sell_controller,
    get_orders_controller,
    cancel_order_controller,
    get_positions_controller,
    get_position_controller,
    close_position_controller,
    get_portfolio_history_controller,
)

__all__ = [
    # Account
    "get_broker_account_controller",
    "get_balances_controller",
    "get_account_activities_controller",
    # Connection Status
    "get_connection_status_controller",
    # SnapTrade Connection
    "snaptrade_register_controller",
    "snaptrade_callback_controller",
    "snaptrade_connect_controller",
    # Trading — Orders
    "buy_controller",
    "sell_controller",
    "get_orders_controller",
    "cancel_order_controller",
    # Trading — Positions
    "get_positions_controller",
    "get_position_controller",
    "close_position_controller",
    # Portfolio
    "get_portfolio_history_controller",
]
