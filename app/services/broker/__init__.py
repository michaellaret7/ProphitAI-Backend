"""
Broker domain services for SnapTrade brokerage operations.

Provides services for:
- Onboarding: user registration and brokerage connection
- Account: balances, equity, buying power
- Trading: buy/sell, orders, positions, portfolio history
- Proposals: trade proposal approval and execution
"""

from app.services.broker.onboarding import (
    register_snaptrade_user,
    save_snaptrade_account,
    get_snaptrade_connect_url,
)
from app.services.broker.account import (
    get_broker_account,
    get_balances,
    get_equity,
    get_buying_power,
    get_cash_balance,
)
from app.services.broker.trading import (
    buy,
    sell,
    get_orders,
    cancel_order,
    get_positions,
    get_position,
    close_position,
    get_portfolio_performance,
    get_portfolio_history,
)
from app.services.broker.proposals import approve_proposal

__all__ = [
    # Onboarding
    'register_snaptrade_user',
    'save_snaptrade_account',
    'get_snaptrade_connect_url',
    # Account
    'get_broker_account',
    'get_balances',
    'get_equity',
    'get_buying_power',
    'get_cash_balance',
    # Trading
    'buy',
    'sell',
    'get_orders',
    'cancel_order',
    'get_positions',
    'get_position',
    'close_position',
    'get_portfolio_performance',
    'get_portfolio_history',
    # Proposals
    'approve_proposal',
]
