"""
SnapTrade Broker API - Unified Interface
Complete one-stop shop for all brokerage operations via SnapTrade.

Sub-components accessible directly:
    broker.auth          — user registration, login, deletion
    broker.accounts      — account info, balances, holdings, positions, orders
    broker.trading       — order execution (equities + options)
    broker.connections   — brokerage authorization management
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from app.brokers.snaptrade.client import SnapTradeClient
from app.brokers.snaptrade.auth import SnapTradeAuth
from app.brokers.snaptrade.accounts import SnapTradeAccounts
from app.brokers.snaptrade.models.activities import ActivityRecord
from app.brokers.snaptrade.models.holdings import STPortfolio
from app.brokers.snaptrade.trading import SnapTradeTrading
from app.brokers.snaptrade.connections import SnapTradeConnections

logger = logging.getLogger(__name__)


class SnapTradeBroker:
    """Unified interface for all SnapTrade brokerage operations."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        consumer_key: Optional[str] = None,
    ):
        self._st_client = SnapTradeClient(
            client_id=client_id, consumer_key=consumer_key,
        )
        self.client = self._st_client.get_client()

        self.auth = SnapTradeAuth(self.client)
        self.accounts = SnapTradeAccounts(self.client)
        self.trading = SnapTradeTrading(self.client)
        self.connections = SnapTradeConnections(self.client)

    # ══════════════════════════════════════════════════════════════
    # AUTH
    # ══════════════════════════════════════════════════════════════

    def register_user(self, user_id: str) -> Dict[str, Any]:
        """Register a new SnapTrade user."""
        return self.auth.register_user(user_id)

    def login_user(
        self,
        user_id: str,
        user_secret: str,
        broker: Optional[str] = None,
        connection_type: str = "trade",
        custom_redirect: Optional[str] = None,
        reconnect: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a login redirect URL for the connection portal (always trade permissions)."""
        return self.auth.login_user(
            user_id, user_secret, broker=broker, connection_type=connection_type,
            custom_redirect=custom_redirect, reconnect=reconnect,
        )

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete a user and all associated data."""
        return self.auth.delete_user(user_id)

    def list_users(self) -> List[str]:
        """List all registered user IDs."""
        return self.auth.list_users()

    def reset_user_secret(self, user_id: str, user_secret: str) -> Dict[str, Any]:
        """Reset a user's secret key."""
        return self.auth.reset_user_secret(user_id, user_secret)

    # ══════════════════════════════════════════════════════════════
    # ACCOUNTS
    # ══════════════════════════════════════════════════════════════

    def list_accounts(self, user_id: str, user_secret: str) -> List[Dict[str, Any]]:
        """List all brokerage accounts for a user."""
        return self.accounts.list_accounts(user_id, user_secret)

    def get_account_details(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> Dict[str, Any]:
        """Get detailed info for a specific account."""
        return self.accounts.get_account_details(user_id, user_secret, account_id)

    def get_balances(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> List[Dict[str, Any]]:
        """Get cash balances for an account."""
        return self.accounts.get_balances(user_id, user_secret, account_id)

    def get_portfolio(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
    ) -> STPortfolio:
        """Get portfolio for an account."""

        kwargs = dict(account_id=account_id, user_id=user_id, user_secret=user_secret)

        with ThreadPoolExecutor(max_workers=2) as pool:
            equity_future = pool.submit(
                self.client.account_information.get_user_account_positions, **kwargs,
            )
            options_future = pool.submit(
                self.client.options.list_option_holdings, **kwargs,
            )

        return STPortfolio.from_raw(
            equity_raw=equity_future.result().body,
            options_raw=options_future.result().body,
        )

    def get_orders(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        start_date: str,
        end_date: str,
    ) -> List[ActivityRecord]:
        """
        Fetch BUY and SELL activities concurrently and return typed records.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Combined list of BUY and SELL ActivityRecord objects
        """
        base_kwargs = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
            "start_date": start_date,
            "end_date": end_date,
        }

        with ThreadPoolExecutor(max_workers=2) as pool:
            buy_future = pool.submit(
                self.accounts._accounts.get_account_activities,
                **base_kwargs, type="BUY",
            )
            sell_future = pool.submit(
                self.accounts._accounts.get_account_activities,
                **base_kwargs, type="SELL",
            )

        # Reason: .body is {"data": [...], "pagination": {...}}
        raw_buys = buy_future.result().body.get("data", [])
        raw_sells = sell_future.result().body.get("data", [])

        return ActivityRecord.from_raw_list(raw_buys + raw_sells)

    # ══════════════════════════════════════════════════════════════
    # TRADING — Equities
    # ══════════════════════════════════════════════════════════════

    def buy(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        symbol: str,
        units: Optional[float] = None,
        notional: Optional[float] = None,
        order_type: str = "Market",
        price: Optional[float] = None,
        stop: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Buy an equity."""
        return self.trading.buy(
            user_id, user_secret, account_id, symbol,
            units=units, notional=notional, order_type=order_type,
            price=price, stop=stop, time_in_force=time_in_force,
        )

    def sell(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        symbol: str,
        units: Optional[float] = None,
        notional: Optional[float] = None,
        order_type: str = "Market",
        price: Optional[float] = None,
        stop: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Sell an equity."""
        return self.trading.sell(
            user_id, user_secret, account_id, symbol,
            units=units, notional=notional, order_type=order_type,
            price=price, stop=stop, time_in_force=time_in_force,
        )

    # ══════════════════════════════════════════════════════════════
    # TRADING — Options Execution
    # ══════════════════════════════════════════════════════════════

    def buy_to_open(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        osi_symbol: str,
        units: int = 1,
        order_type: str = "Market",
        price: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Buy to open an options contract (OSI symbol auto-converted to OCC)."""
        return self.trading.buy_to_open(
            user_id, user_secret, account_id, osi_symbol,
            units=units, order_type=order_type, price=price,
            time_in_force=time_in_force,
        )

    def sell_to_close(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        osi_symbol: str,
        units: int = 1,
        order_type: str = "Market",
        price: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Sell to close an options contract (OSI symbol auto-converted to OCC)."""
        return self.trading.sell_to_close(
            user_id, user_secret, account_id, osi_symbol,
            units=units, order_type=order_type, price=price,
            time_in_force=time_in_force,
        )

    def sell_to_open(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        osi_symbol: str,
        units: int = 1,
        order_type: str = "Market",
        price: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Sell to open an options contract (OSI symbol auto-converted to OCC)."""
        return self.trading.sell_to_open(
            user_id, user_secret, account_id, osi_symbol,
            units=units, order_type=order_type, price=price,
            time_in_force=time_in_force,
        )

    def buy_to_close(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        osi_symbol: str,
        units: int = 1,
        order_type: str = "Market",
        price: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Buy to close an options contract (OSI symbol auto-converted to OCC)."""
        return self.trading.buy_to_close(
            user_id, user_secret, account_id, osi_symbol,
            units=units, order_type=order_type, price=price,
            time_in_force=time_in_force,
        )

    def place_multi_leg_order(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        legs: List[Dict[str, Any]],
        order_type: str = "Market",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "Day",
    ) -> Dict[str, Any]:
        """Place a multi-leg options order (OSI symbols auto-converted to OCC)."""
        return self.trading.place_multi_leg_order(
            user_id, user_secret, account_id, legs,
            order_type=order_type, limit_price=limit_price,
            stop_price=stop_price, time_in_force=time_in_force,
        )

    # ══════════════════════════════════════════════════════════════
    # TRADING — Order Management
    # ══════════════════════════════════════════════════════════════

    def cancel_order(
        self, user_id: str, user_secret: str, account_id: str,
        brokerage_order_id: str,
    ) -> Dict[str, Any]:
        """Cancel an open order."""
        return self.trading.cancel_order(
            user_id, user_secret, account_id, brokerage_order_id,
        )

    def replace_order(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        brokerage_order_id: str,
        action: str,
        order_type: str,
        time_in_force: str = "Day",
        symbol: Optional[str] = None,
        units: Optional[float] = None,
        price: Optional[float] = None,
        stop: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Replace (modify) an existing open order."""
        return self.trading.replace_order(
            user_id, user_secret, account_id, brokerage_order_id,
            action=action, order_type=order_type, time_in_force=time_in_force,
            symbol=symbol, units=units, price=price, stop=stop,
        )

    def get_order_impact(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        symbol: str,
        action: str,
        units: float,
        order_type: str = "Market",
        time_in_force: str = "Day",
        price: Optional[float] = None,
        stop: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Preview the impact of an order before placing it."""
        return self.trading.get_order_impact(
            user_id, user_secret, account_id, symbol, action, units,
            order_type=order_type, time_in_force=time_in_force,
            price=price, stop=stop,
        )

    def get_quotes(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        symbols: str,
        use_ticker: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get real-time quotes for symbols."""
        return self.trading.get_quotes(
            user_id, user_secret, account_id, symbols, use_ticker=use_ticker,
        )

    # ══════════════════════════════════════════════════════════════
    # CONNECTIONS
    # ══════════════════════════════════════════════════════════════

    def list_connections(
        self, user_id: str, user_secret: str,
    ) -> List[Dict[str, Any]]:
        """List all brokerage authorizations for a user."""
        return self.connections.list_authorizations(user_id, user_secret)

    def get_connection(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> Dict[str, Any]:
        """Get details for a specific brokerage authorization."""
        return self.connections.get_authorization(
            user_id, user_secret, authorization_id,
        )

    def refresh_connection(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> Dict[str, Any]:
        """Refresh a brokerage authorization."""
        return self.connections.refresh_authorization(
            user_id, user_secret, authorization_id,
        )

    def disable_connection(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> Dict[str, Any]:
        """Disable a brokerage authorization."""
        return self.connections.disable_authorization(
            user_id, user_secret, authorization_id,
        )

    def remove_connection(
        self, user_id: str, user_secret: str, authorization_id: str,
    ) -> None:
        """Permanently remove a brokerage authorization."""
        self.connections.remove_authorization(
            user_id, user_secret, authorization_id,
        )


