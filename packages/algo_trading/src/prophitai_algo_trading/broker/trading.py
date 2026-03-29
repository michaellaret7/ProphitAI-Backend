"""
Alpaca Trading Operations
Handles order execution: buying, selling, and order management
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TrailingStopOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
    ReplaceOrderRequest,
    ClosePositionRequest,
    GetOrderByIdRequest,
    OptionLegRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, PositionIntent
from typing import Optional, Dict, List

class AlpacaTrading:
    """Handles order execution and trading operations."""

    def __init__(self, client: TradingClient):
        self.client = client

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _parse_time_in_force(time_in_force: str) -> TimeInForce:
        """Convert string to TimeInForce enum."""
        tif_map = {
            'day': TimeInForce.DAY, 'gtc': TimeInForce.GTC,
            'ioc': TimeInForce.IOC, 'fok': TimeInForce.FOK,
            'opg': TimeInForce.OPG, 'cls': TimeInForce.CLS,
        }
        return tif_map.get(time_in_force.lower(), TimeInForce.DAY)

    @staticmethod
    def _parse_order_class(order_class: Optional[str]) -> Optional[OrderClass]:
        """Convert string to OrderClass enum."""
        if not order_class:
            return None
        oc_map = {
            'simple': OrderClass.SIMPLE, 'bracket': OrderClass.BRACKET,
            'oco': OrderClass.OCO, 'oto': OrderClass.OTO, 'mleg': OrderClass.MLEG,
        }
        result = oc_map.get(order_class.lower())
        if result is None:
            raise ValueError(f"Invalid order_class '{order_class}'. Must be: simple, bracket, oco, oto, mleg")
        return result

    @staticmethod
    def _parse_position_intent(intent: Optional[str]) -> Optional[PositionIntent]:
        """Convert string to PositionIntent enum."""
        if not intent:
            return None
        intent_map = {
            'buy_to_open': PositionIntent.BUY_TO_OPEN,
            'buy_to_close': PositionIntent.BUY_TO_CLOSE,
            'sell_to_open': PositionIntent.SELL_TO_OPEN,
            'sell_to_close': PositionIntent.SELL_TO_CLOSE,
        }
        result = intent_map.get(intent.lower())
        if result is None:
            raise ValueError(f"Invalid position_intent '{intent}'. Must be: buy_to_open, buy_to_close, sell_to_open, sell_to_close")
        return result

    @classmethod
    def _format_order_response(cls, order) -> Dict:
        """Format order response into standardized dict."""
        result = {
            'id': str(order.id),
            'symbol': order.symbol,
            'qty': float(order.qty) if order.qty else None,
            'notional': float(order.notional) if order.notional else None,
            'side': order.side,
            'type': order.order_type,
            'order_class': order.order_class,
            'status': order.status,
            'limit_price': float(order.limit_price) if order.limit_price else None,
            'stop_price': float(order.stop_price) if order.stop_price else None,
            'trail_price': float(order.trail_price) if order.trail_price else None,
            'trail_percent': float(order.trail_percent) if order.trail_percent else None,
            'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
            'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
        }
        # Reason: Include nested legs for multi-leg and bracket orders
        if getattr(order, 'legs', None):
            result['legs'] = [cls._format_order_response(leg) for leg in order.legs]
        return result

    @staticmethod
    def _is_crypto(symbol: str) -> bool:
        """Check if a symbol is a crypto pair (e.g. BTCUSD, ETH/USD)."""
        cleaned = symbol.replace("/", "").upper()
        return cleaned.endswith("USD") and len(cleaned) in (6, 7, 8)

    def _submit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        stop_loss_limit: Optional[float] = None,
        order_class: Optional[str] = None,
        time_in_force: str = 'day',
    ) -> Dict:
        """Submit an order. Type inferred from params: trailing stop > stop-limit > stop > limit > market."""
        # Reason: Alpaca crypto orders only support 'gtc' time-in-force
        if self._is_crypto(symbol) and time_in_force == 'day':
            time_in_force = 'gtc'
        tif = self._parse_time_in_force(time_in_force)
        oc = self._parse_order_class(order_class)

        tp_req = TakeProfitRequest(limit_price=take_profit) if take_profit else None
        sl_req = StopLossRequest(stop_price=stop_loss, limit_price=stop_loss_limit) if stop_loss else None

        common = dict(
            symbol=symbol, qty=qty, notional=notional, side=side,
            time_in_force=tif, order_class=oc, take_profit=tp_req, stop_loss=sl_req,
        )

        try:
            if trail_price is not None or trail_percent is not None:
                order_data = TrailingStopOrderRequest(**common, trail_price=trail_price, trail_percent=trail_percent)
            elif stop_price and limit_price:
                order_data = StopLimitOrderRequest(**common, stop_price=stop_price, limit_price=limit_price)
            elif stop_price:
                order_data = StopOrderRequest(**common, stop_price=stop_price)
            elif limit_price:
                order_data = LimitOrderRequest(**common, limit_price=limit_price)
            else:
                order_data = MarketOrderRequest(**common)

            order = self.client.submit_order(order_data=order_data)
            return self._format_order_response(order)
        except Exception as e:
            action = "buy" if side == OrderSide.BUY else "sell"
            raise Exception(f"Failed to {action} {symbol}: {str(e)}")

    # ── Public methods ────────────────────────────────────────────────

    def buy(self, symbol: str, **kwargs) -> Dict:
        """Buy an asset. See _submit_order for full parameter docs."""
        return self._submit_order(symbol=symbol, side=OrderSide.BUY, **kwargs)

    def sell(self, symbol: str, **kwargs) -> Dict:
        """Sell an asset. See _submit_order for full parameter docs."""
        return self._submit_order(symbol=symbol, side=OrderSide.SELL, **kwargs)

    def close_position(
        self, symbol: str, qty: Optional[float] = None, percentage: Optional[float] = None,
    ) -> Dict:
        """Close a position fully or partially. Provide qty or percentage for partial, neither for full."""
        close_options = None
        if qty is not None and percentage is not None:
            raise ValueError("Provide qty or percentage, not both.")
        if qty is not None:
            close_options = ClosePositionRequest(qty=str(qty))
        elif percentage is not None:
            close_options = ClosePositionRequest(percentage=str(percentage))

        try:
            order = self.client.close_position(symbol, close_options=close_options)
            return {
                'id': str(order.id), 'symbol': order.symbol,
                'qty': float(order.qty) if order.qty else None, 'status': order.status,
            }
        except Exception as e:
            raise Exception(f"Failed to close position for {symbol}: {str(e)}")

    def close_all_positions(self, cancel_orders: bool = True) -> List[Dict]:
        """Close all positions. Optionally cancels open orders first."""
        try:
            orders = self.client.close_all_positions(cancel_orders=cancel_orders)
            return [{'id': str(o.id), 'symbol': o.symbol, 'status': o.status} for o in orders]
        except Exception as e:
            raise Exception(f"Failed to close all positions: {str(e)}")

    def cancel_order(self, order_id: str) -> None:
        """Cancel a specific order by ID."""
        try:
            self.client.cancel_order_by_id(order_id)
        except Exception as e:
            raise Exception(f"Failed to cancel order {order_id}: {str(e)}")

    def cancel_all_orders(self) -> None:
        """Cancel all open orders."""
        try:
            self.client.cancel_orders()
        except Exception as e:
            raise Exception(f"Failed to cancel all orders: {str(e)}")

    def replace_order(
        self, order_id: str, qty: Optional[int] = None, limit_price: Optional[float] = None,
        stop_price: Optional[float] = None, trail: Optional[float] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict:
        """Modify an existing open order (qty, limit_price, stop_price, trail, time_in_force)."""
        tif = self._parse_time_in_force(time_in_force) if time_in_force else None
        try:
            order = self.client.replace_order_by_id(
                order_id=order_id,
                order_data=ReplaceOrderRequest(
                    qty=qty, limit_price=limit_price, stop_price=stop_price,
                    trail=trail, time_in_force=tif,
                ),
            )
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed to replace order {order_id}: {str(e)}")

    def get_order_by_id(self, order_id: str, nested: bool = True) -> Dict:
        """Retrieve a specific order by UUID. Set nested=True for leg details."""
        try:
            order = self.client.get_order_by_id(
                order_id=order_id,
                filter=GetOrderByIdRequest(nested=nested),
            )
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed to get order {order_id}: {str(e)}")

    def exercise_options_position(self, symbol_or_contract_id: str) -> None:
        """Exercise a held options position (OSI symbol or contract UUID)."""
        try:
            self.client.exercise_options_position(symbol_or_contract_id=symbol_or_contract_id)
        except Exception as e:
            raise Exception(f"Failed to exercise option {symbol_or_contract_id}: {str(e)}")

    def submit_multi_leg_order(
        self, legs: List[Dict], qty: int,
        limit_price: Optional[float] = None, time_in_force: str = 'day',
    ) -> Dict:
        """Submit a multi-leg option order (spreads, straddles, iron condors, etc.)."""
        tif = self._parse_time_in_force(time_in_force)

        leg_requests = []
        for leg in legs:
            side_str = leg.get('side')
            intent_str = leg.get('position_intent')
            side_enum = {'buy': OrderSide.BUY, 'sell': OrderSide.SELL}.get(side_str.lower()) if side_str else None
            intent_enum = self._parse_position_intent(intent_str)

            leg_requests.append(OptionLegRequest(
                symbol=leg['symbol'], ratio_qty=leg.get('ratio_qty', 1),
                side=side_enum, position_intent=intent_enum,
            ))

        common = dict(qty=qty, time_in_force=tif, order_class=OrderClass.MLEG, legs=leg_requests)

        try:
            if limit_price is not None:
                order_data = LimitOrderRequest(**common, limit_price=limit_price)
            else:
                order_data = MarketOrderRequest(**common)

            order = self.client.submit_order(order_data=order_data)
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed to submit multi-leg order: {str(e)}")
