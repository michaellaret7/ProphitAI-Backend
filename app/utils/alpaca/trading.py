"""
Alpaca Trading Operations
Handles order execution: buying, selling, and order management
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce
from typing import Optional, Dict, List


class AlpacaTrading:
    """Handles order execution and trading operations"""

    def __init__(self, client: TradingClient):
        """
        Initialize trading operations

        Args:
            client: Initialized TradingClient instance
        """
        self.client = client

    @staticmethod
    def _parse_time_in_force(time_in_force: str) -> TimeInForce:
        """Convert string time_in_force to enum"""
        tif_map = {
            'day': TimeInForce.DAY,
            'gtc': TimeInForce.GTC,
            'ioc': TimeInForce.IOC,
            'fok': TimeInForce.FOK
        }
        return tif_map.get(time_in_force.lower(), TimeInForce.DAY)

    @staticmethod
    def _format_order_response(order) -> Dict:
        """Format order response into standardized dict"""
        return {
            'id': str(order.id),
            'symbol': order.symbol,
            'qty': float(order.qty) if order.qty else None,
            'notional': float(order.notional) if order.notional else None,
            'side': order.side,
            'type': order.order_type,
            'status': order.status,
            'limit_price': float(order.limit_price) if order.limit_price else None,
            'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
            'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
        }

    def _submit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        limit_price: Optional[float] = None,
        time_in_force: str = 'day'
    ) -> Dict:
        """
        Internal method to submit an order

        Args:
            symbol: Stock symbol or crypto pair
            side: OrderSide.BUY or OrderSide.SELL
            qty: Number of shares (use qty or notional, not both)
            notional: Dollar amount (use qty or notional, not both)
            limit_price: Price for limit order. None for market order
            time_in_force: 'day', 'gtc', 'ioc', 'fok'

        Returns:
            Order details dict
        """
        tif = self._parse_time_in_force(time_in_force)

        try:
            if limit_price:
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    notional=notional,
                    side=side,
                    time_in_force=tif,
                    limit_price=limit_price
                )
            else:
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    notional=notional,
                    side=side,
                    time_in_force=tif
                )

            order = self.client.submit_order(order_data=order_data)
            return self._format_order_response(order)

        except Exception as e:
            action = "buy" if side == OrderSide.BUY else "sell"
            raise Exception(f"Failed to {action} {symbol}: {str(e)}")

    def buy(
        self,
        symbol: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        limit_price: Optional[float] = None,
        time_in_force: str = 'day'
    ) -> Dict:
        """
        Buy an asset

        Args:
            symbol: Stock symbol (e.g., 'AAPL') or crypto pair (e.g., 'BTC/USD')
            qty: Number of shares to buy (use either qty or notional, not both)
            notional: Dollar amount to spend (use either qty or notional, not both)
            limit_price: If set, creates a limit order at this price. If None, creates market order
            time_in_force: 'day', 'gtc' (good till canceled), 'ioc' (immediate or cancel), 'fok' (fill or kill)

        Returns:
            Order details dict
        """
        return self._submit_order(
            symbol=symbol,
            side=OrderSide.BUY,
            qty=qty,
            notional=notional,
            limit_price=limit_price,
            time_in_force=time_in_force
        )

    def sell(
        self,
        symbol: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        limit_price: Optional[float] = None,
        time_in_force: str = 'day'
    ) -> Dict:
        """
        Sell an asset

        Args:
            symbol: Stock symbol (e.g., 'AAPL') or crypto pair (e.g., 'BTC/USD')
            qty: Number of shares to sell (use either qty or notional, not both)
            notional: Dollar amount to sell (use either qty or notional, not both)
            limit_price: If set, creates a limit order at this price. If None, creates market order
            time_in_force: 'day', 'gtc' (good till canceled), 'ioc' (immediate or cancel), 'fok' (fill or kill)

        Returns:
            Order details dict
        """
        return self._submit_order(
            symbol=symbol,
            side=OrderSide.SELL,
            qty=qty,
            notional=notional,
            limit_price=limit_price,
            time_in_force=time_in_force
        )

    def close_position(self, symbol: str) -> Dict:
        """
        Close a position for a specific symbol

        Args:
            symbol: Symbol to close position for

        Returns:
            Order details dict
        """
        try:
            order = self.client.close_position(symbol)
            return {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty) if order.qty else None,
                'status': order.status
            }
        except Exception as e:
            raise Exception(f"Failed to close position for {symbol}: {str(e)}")

    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict]:
        """
        Close all positions

        Args:
            cancel_orders: Whether to cancel open orders first

        Returns:
            List of order details dicts
        """
        try:
            orders = self.client.close_all_positions(cancel_orders=cancel_orders)
            return [
                {
                    'id': str(order.id),
                    'symbol': order.symbol,
                    'status': order.status
                }
                for order in orders
            ]
        except Exception as e:
            raise Exception(f"Failed to close all positions: {str(e)}")

    def cancel_order(self, order_id: str) -> None:
        """
        Cancel a specific order

        Args:
            order_id: ID of order to cancel
        """
        try:
            self.client.cancel_order_by_id(order_id)
        except Exception as e:
            raise Exception(f"Failed to cancel order {order_id}: {str(e)}")

    def cancel_all_orders(self) -> None:
        """Cancel all open orders"""
        try:
            self.client.cancel_orders()
        except Exception as e:
            raise Exception(f"Failed to cancel all orders: {str(e)}")
