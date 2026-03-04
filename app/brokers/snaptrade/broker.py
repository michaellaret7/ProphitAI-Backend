"""
SnapTrade Broker API - Unified Interface
Complete one-stop shop for all brokerage operations via SnapTrade.

Sub-components accessible directly:
    broker.auth          — user registration, login, deletion
    broker.accounts      — account info, balances, holdings, positions, orders
    broker.trading       — order execution (equities + options)
    broker.connections   — brokerage authorization management
    broker.reporting     — activities, performance reports
    broker.options       — options chains, quotes, snapshots (via Alpaca)
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from app.brokers.snaptrade.client import SnapTradeClient
from app.brokers.snaptrade.auth import SnapTradeAuth
from app.brokers.snaptrade.accounts import SnapTradeAccounts
from app.brokers.snaptrade.models.positions import Position
from app.brokers.snaptrade.trading import SnapTradeTrading
from app.brokers.snaptrade.connections import SnapTradeConnections
from app.brokers.snaptrade.reporting import SnapTradeReporting

logger = logging.getLogger(__name__)


class SnapTradeBroker:
    """Unified interface for all SnapTrade brokerage operations."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        consumer_key: Optional[str] = None,
        alpaca_options_feed: str = "indicative",
    ):
        self._st_client = SnapTradeClient(
            client_id=client_id, consumer_key=consumer_key,
        )
        client = self._st_client.get_client()

        self.auth = SnapTradeAuth(client)
        self.accounts = SnapTradeAccounts(client)
        self.trading = SnapTradeTrading(client)
        self.connections = SnapTradeConnections(client)
        self.reporting = SnapTradeReporting(client)

        # Reason: SnapTrade's options chain endpoint returns 500 for Alpaca Paper,
        # so options DATA comes from Alpaca's native API while options EXECUTION
        # goes through SnapTrade.
        self.options = self._init_options_service(alpaca_options_feed)

    @staticmethod
    def _init_options_service(feed: str):
        """Initialize Alpaca options data service if credentials are available."""
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")

        if not api_key or not secret_key:
            logger.warning(
                "ALPACA_API_KEY / ALPACA_SECRET_KEY not set. "
                "Options data (chains, quotes, greeks) will be unavailable."
            )
            return None

        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical.option import OptionHistoricalDataClient
            from app.brokers.alpaca_broker.options import BrokerOptionsService

            trading_client = TradingClient(
                api_key=api_key, secret_key=secret_key, paper=True,
            )
            option_data_client = OptionHistoricalDataClient(
                api_key=api_key, secret_key=secret_key,
            )
            return BrokerOptionsService(
                trading_client=trading_client,
                option_data_client=option_data_client,
                feed=feed,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Alpaca options service: {e}")
            return None

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
        connection_type: Optional[str] = None,
        custom_redirect: Optional[str] = None,
        reconnect: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a login redirect URL for the connection portal."""
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

    def get_holdings(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> Dict[str, Any]:
        """Get full holdings (positions + balances + orders)."""
        return self.accounts.get_holdings(user_id, user_secret, account_id)

    def get_all_holdings(
        self, user_id: str, user_secret: str,
    ) -> List[Dict[str, Any]]:
        """Get holdings across all accounts."""
        return self.accounts.get_all_holdings(user_id, user_secret)

    def get_positions(
        self, user_id: str, user_secret: str, account_id: str,
    ) -> List[Position]:
        """Get open positions for an account."""
        return self.accounts.get_positions(user_id, user_secret, account_id)

    def get_orders(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        state: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get orders for an account."""
        return self.accounts.get_orders(
            user_id, user_secret, account_id, state=state, days=days,
        )

    def get_account_activities(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get account activities (fills, dividends, transfers, etc.)."""
        return self.accounts.get_activities(
            user_id, user_secret, account_id,
            start_date=start_date, end_date=end_date, type=type,
        )

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

    # ══════════════════════════════════════════════════════════════
    # REPORTING
    # ══════════════════════════════════════════════════════════════

    def get_activities(
        self,
        user_id: str,
        user_secret: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        accounts: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get transaction activities across accounts."""
        return self.reporting.get_activities(
            user_id, user_secret,
            start_date=start_date, end_date=end_date, accounts=accounts,
        )

    def get_performance_report(
        self,
        user_id: str,
        user_secret: str,
        start_date: str,
        end_date: str,
        accounts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get portfolio performance report."""
        return self.reporting.get_performance_report(
            user_id, user_secret, start_date, end_date, accounts=accounts,
        )

    # ══════════════════════════════════════════════════════════════
    # OPTIONS DATA (via Alpaca)
    # ══════════════════════════════════════════════════════════════

    def get_options_chain(
        self,
        underlying: str,
        expiration: Optional[str] = None,
        limit: Optional[int] = None,
        return_df: Optional[bool] = None,
    ):
        """Get options chain with quotes and greeks (via Alpaca)."""
        if self.options is None:
            raise RuntimeError(
                "Options data unavailable — ALPACA_API_KEY / ALPACA_SECRET_KEY not configured."
            )
        return self.options.get_options_chain(
            underlying=underlying, expiration=expiration,
            limit=limit, return_df=return_df,
        )

    def get_option_expirations(
        self, underlying: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[str]:
        """Get available expiration dates (via Alpaca)."""
        if self.options is None:
            raise RuntimeError("Options data unavailable — Alpaca credentials not configured.")
        return self.options.get_available_dates(underlying=underlying, start=start, end=end)

    def get_option_contracts(
        self,
        underlying: str,
        expiration: Optional[str] = None,
        contract_type: Optional[str] = None,
        strike_range: Optional[Tuple[float, float]] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Get available option contracts (via Alpaca)."""
        if self.options is None:
            raise RuntimeError("Options data unavailable — Alpaca credentials not configured.")
        return self.options.get_available_contracts(
            underlying=underlying, expiration=expiration,
            contract_type=contract_type, strike_range=strike_range, limit=limit,
        )

    def get_option_latest_quote(self, symbol: str) -> Dict:
        """Get latest bid/ask quote for an option contract (via Alpaca)."""
        if self.options is None:
            raise RuntimeError("Options data unavailable — Alpaca credentials not configured.")
        return self.options.get_option_latest_quote(symbol)

    def get_option_snapshot(self, symbol: str) -> Dict:
        """Get full snapshot (quote + trade + greeks) for an option (via Alpaca)."""
        if self.options is None:
            raise RuntimeError("Options data unavailable — Alpaca credentials not configured.")
        return self.options.get_option_snapshot(symbol)
