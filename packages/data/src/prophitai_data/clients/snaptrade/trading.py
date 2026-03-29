"""
SnapTrade Trading Service
Handles order execution for equities and options via SnapTrade.
Options accept OSI symbols and auto-convert to OCC format.
"""

from typing import Any, Dict, List, Optional

from snaptrade_client import SnapTrade

from prophitai_data.clients.snaptrade.utils import extract_body, osi_to_occ


class SnapTradeTrading:
    """Order execution for equities and options via SnapTrade."""

    def __init__(self, client: SnapTrade):
        self._trading = client.trading

    # ================================
    # --> Helper funcs
    # ================================

    def place_order(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        action: str,
        symbol: str,
        order_type: str = "Market",
        time_in_force: str = "Day",
        units: Optional[float] = None,
        notional_value: Optional[float] = None,
        price: Optional[float] = None,
        stop: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Core order placement via place_force_order.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            action: Order action ('BUY', 'SELL', 'BUY_TO_OPEN', 'SELL_TO_CLOSE', etc.)
            symbol: Ticker or OCC option symbol
            order_type: 'Market', 'Limit', 'Stop', 'StopLimit'
            time_in_force: 'Day', 'GTC', 'FOK', 'IOC'
            units: Number of shares/contracts
            notional_value: Dollar amount (equities only)
            price: Limit price (required for Limit/StopLimit orders)
            stop: Stop price (required for Stop/StopLimit orders)

        Returns:
            Order response dict
        """
        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
            "action": action,
            "symbol": symbol,
            "order_type": order_type,
            "time_in_force": time_in_force,
        }
        if units is not None:
            kwargs["units"] = units
        if notional_value is not None:
            kwargs["notional_value"] = notional_value
        if price is not None:
            kwargs["price"] = price
        if stop is not None:
            kwargs["stop"] = stop

        response = self._trading.place_force_order(**kwargs)
        return extract_body(response)

    # ================================
    # --> Equity convenience methods
    # ================================

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
        """
        Buy an equity.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            symbol: Ticker symbol (e.g. 'AAPL')
            units: Number of shares
            notional: Dollar amount (alternative to units)
            order_type: 'Market', 'Limit', 'Stop', 'StopLimit'
            price: Limit price
            stop: Stop price
            time_in_force: 'Day', 'GTC', 'FOK', 'IOC'
        """
        return self.place_order(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
            action="BUY", symbol=symbol, order_type=order_type,
            time_in_force=time_in_force, units=units,
            notional_value=notional, price=price, stop=stop,
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
        """
        Sell an equity.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            symbol: Ticker symbol (e.g. 'AAPL')
            units: Number of shares
            notional: Dollar amount (alternative to units)
            order_type: 'Market', 'Limit', 'Stop', 'StopLimit'
            price: Limit price
            stop: Stop price
            time_in_force: 'Day', 'GTC', 'FOK', 'IOC'
        """
        return self.place_order(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
            action="SELL", symbol=symbol, order_type=order_type,
            time_in_force=time_in_force, units=units,
            notional_value=notional, price=price, stop=stop,
        )

    # ================================
    # --> Options convenience methods
    # ================================

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
        """
        Buy to open an options contract. Accepts OSI symbol, auto-converts to OCC.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            osi_symbol: Alpaca OSI symbol (e.g. 'CRWV260327C00120000')
            units: Number of contracts
            order_type: 'Market' or 'Limit'
            price: Limit price (required for Limit orders)
            time_in_force: 'Day', 'GTC'
        """
        return self.place_order(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
            action="BUY_TO_OPEN", symbol=osi_to_occ(osi_symbol),
            order_type=order_type, time_in_force=time_in_force,
            units=units, price=price,
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
        """
        Sell to close an options contract. Accepts OSI symbol, auto-converts to OCC.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            osi_symbol: Alpaca OSI symbol
            units: Number of contracts
            order_type: 'Market' or 'Limit'
            price: Limit price
            time_in_force: 'Day', 'GTC'
        """
        return self.place_order(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
            action="SELL_TO_CLOSE", symbol=osi_to_occ(osi_symbol),
            order_type=order_type, time_in_force=time_in_force,
            units=units, price=price,
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
        """
        Sell to open an options contract. Accepts OSI symbol, auto-converts to OCC.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            osi_symbol: Alpaca OSI symbol
            units: Number of contracts
            order_type: 'Market' or 'Limit'
            price: Limit price
            time_in_force: 'Day', 'GTC'
        """
        return self.place_order(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
            action="SELL_TO_OPEN", symbol=osi_to_occ(osi_symbol),
            order_type=order_type, time_in_force=time_in_force,
            units=units, price=price,
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
        """
        Buy to close an options contract. Accepts OSI symbol, auto-converts to OCC.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            osi_symbol: Alpaca OSI symbol
            units: Number of contracts
            order_type: 'Market' or 'Limit'
            price: Limit price
            time_in_force: 'Day', 'GTC'
        """
        return self.place_order(
            user_id=user_id, user_secret=user_secret, account_id=account_id,
            action="BUY_TO_CLOSE", symbol=osi_to_occ(osi_symbol),
            order_type=order_type, time_in_force=time_in_force,
            units=units, price=price,
        )

    # ================================
    # --> Multi-leg options
    # ================================

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
        """
        Place a multi-leg options order (spreads, straddles, etc.).
        Each leg's OSI symbol is auto-converted to OCC format.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            legs: List of leg dicts, each with:
                - 'symbol': OSI option symbol
                - 'action': 'BUY_TO_OPEN', 'SELL_TO_OPEN', etc.
                - 'units': Number of contracts (default 1)
            order_type: 'Market', 'Limit', 'Stop', 'StopLimit'
            limit_price: Net debit/credit limit price
            stop_price: Stop price
            time_in_force: 'Day', 'GTC'

        Returns:
            Order response dict
        """
        # Reason: SDK expects uppercase order_type (MARKET, LIMIT, etc.)
        order_type_map = {
            "Market": "MARKET", "Limit": "LIMIT",
            "Stop": "STOP_LOSS_MARKET", "StopLimit": "STOP_LOSS_LIMIT",
        }
        sdk_order_type = order_type_map.get(order_type, order_type.upper())

        # Reason: SDK expects each leg as {instrument: {symbol, instrument_type}, action, units}
        converted_legs = []
        for leg in legs:
            converted_legs.append({
                "instrument": {
                    "symbol": osi_to_occ(leg["symbol"]),
                    "instrument_type": "OPTION",
                },
                "action": leg["action"].upper(),
                "units": leg.get("units", 1),
            })

        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
            "legs": converted_legs,
            "order_type": sdk_order_type,
            "time_in_force": time_in_force,
        }
        if limit_price is not None:
            kwargs["limit_price"] = str(limit_price)
        if stop_price is not None:
            kwargs["stop_price"] = str(stop_price)

        response = self._trading.place_mleg_order(**kwargs)
        return extract_body(response)

    # ================================
    # --> Order management
    # ================================

    def cancel_order(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        brokerage_order_id: str,
    ) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            brokerage_order_id: Order ID from the brokerage
        """
        response = self._trading.cancel_order(
            user_id=user_id, user_secret=user_secret,
            account_id=account_id, brokerage_order_id=brokerage_order_id,
        )
        return extract_body(response)

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
        """
        Replace (modify) an existing open order.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            brokerage_order_id: Order ID to replace
            action: Order action ('BUY', 'SELL', etc.)
            order_type: 'Market', 'Limit', 'Stop', 'StopLimit'
            time_in_force: 'Day', 'GTC'
            symbol: Ticker symbol
            units: New quantity
            price: New limit price
            stop: New stop price
        """
        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
            "brokerage_order_id": brokerage_order_id,
            "action": action,
            "order_type": order_type,
            "time_in_force": time_in_force,
        }
        if symbol is not None:
            kwargs["symbol"] = symbol
        if units is not None:
            kwargs["units"] = units
        if price is not None:
            kwargs["price"] = price
        if stop is not None:
            kwargs["stop"] = stop

        response = self._trading.replace_order(**kwargs)
        return extract_body(response)

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
        """
        Preview the impact of an order before placing it.

        Resolves ticker symbol to SnapTrade universal_symbol_id via quotes,
        then calls the order impact endpoint.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            symbol: Ticker symbol (e.g. 'AAPL')
            action: 'BUY', 'SELL', etc.
            units: Number of shares/contracts
            order_type: 'Market', 'Limit', 'Stop', 'StopLimit'
            time_in_force: 'Day', 'GTC'
            price: Limit price
            stop: Stop price
        """
        # Reason: get_order_impact requires universal_symbol_id (UUID), not ticker.
        # Resolve by fetching a quote which returns the symbol metadata.
        quotes = self.get_quotes(
            user_id=user_id, user_secret=user_secret,
            account_id=account_id, symbols=symbol, use_ticker=True,
        )
        if not quotes:
            raise ValueError(f"Could not resolve symbol '{symbol}' to a SnapTrade universal symbol ID")

        universal_id = quotes[0].get("symbol", {}).get("id")
        if not universal_id:
            raise ValueError(f"Quote for '{symbol}' did not contain a universal symbol ID")

        kwargs: Dict[str, Any] = {
            "user_id": user_id,
            "user_secret": user_secret,
            "account_id": account_id,
            "action": action,
            "universal_symbol_id": universal_id,
            "order_type": order_type,
            "time_in_force": time_in_force,
            "units": float(units),
        }
        if price is not None:
            kwargs["price"] = float(price)
        if stop is not None:
            kwargs["stop"] = float(stop)

        response = self._trading.get_order_impact(**kwargs)
        return extract_body(response)

    def get_quotes(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        symbols: str,
        use_ticker: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get real-time quotes for one or more symbols.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret
            account_id: Brokerage account ID
            symbols: Comma-separated ticker symbols
            use_ticker: Use ticker symbols instead of universal IDs
        """
        response = self._trading.get_user_account_quotes(
            user_id=user_id, user_secret=user_secret,
            account_id=account_id, symbols=symbols,
            use_ticker=use_ticker,
        )
        return extract_body(response)
