"""
Alpaca Broker Trading Operations
Handles order execution on behalf of end user accounts.

Mirrors: app/brokers/alpaca/trading.py
Key difference: Every method takes account_id as first param.
Uses submit_order_for_account() instead of submit_order().
"""

from alpaca.broker.client import BrokerClient
from alpaca.broker.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TrailingStopOrderRequest,
)
from alpaca.trading.requests import (
    TakeProfitRequest,
    StopLossRequest,
    ReplaceOrderRequest,
    ClosePositionRequest,
    GetOrderByIdRequest,
    GetOrdersRequest,
    OptionLegRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderClass,
    PositionIntent,
    QueryOrderStatus,
)
from typing import Optional, Dict, List


class BrokerTrading:
    """Handles order execution for end user accounts via Broker API."""

    def __init__(self, client: BrokerClient):
        self.client = client

    # ── Private helpers (identical to your trading.py) ─────────────

    @staticmethod
    def _parse_time_in_force(time_in_force: str) -> TimeInForce:
        """Convert string to TimeInForce enum."""
        tif_map = {
            "day": TimeInForce.DAY, "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC, "fok": TimeInForce.FOK,
            "opg": TimeInForce.OPG, "cls": TimeInForce.CLS,
        }
        return tif_map.get(time_in_force.lower(), TimeInForce.DAY)

    @staticmethod
    def _parse_order_class(order_class: Optional[str]) -> Optional[OrderClass]:
        """Convert string to OrderClass enum."""
        if not order_class:
            return None
        oc_map = {
            "simple": OrderClass.SIMPLE, "bracket": OrderClass.BRACKET,
            "oco": OrderClass.OCO, "oto": OrderClass.OTO, "mleg": OrderClass.MLEG,
        }
        result = oc_map.get(order_class.lower())
        if result is None:
            raise ValueError(
                f"Invalid order_class '{order_class}'. Must be: simple, bracket, oco, oto, mleg"
            )
        return result

    @staticmethod
    def _parse_position_intent(intent: Optional[str]) -> Optional[PositionIntent]:
        """Convert string to PositionIntent enum."""
        if not intent:
            return None
        intent_map = {
            "buy_to_open": PositionIntent.BUY_TO_OPEN,
            "buy_to_close": PositionIntent.BUY_TO_CLOSE,
            "sell_to_open": PositionIntent.SELL_TO_OPEN,
            "sell_to_close": PositionIntent.SELL_TO_CLOSE,
        }
        result = intent_map.get(intent.lower())
        if result is None:
            raise ValueError(
                f"Invalid position_intent '{intent}'. "
                "Must be: buy_to_open, buy_to_close, sell_to_open, sell_to_close"
            )
        return result

    @classmethod
    def _format_order_response(cls, order) -> Dict:
        """Format order response into standardized dict."""
        result = {
            "id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty) if order.qty else None,
            "notional": float(order.notional) if order.notional else None,
            "side": str(order.side),
            "type": str(order.order_type),
            "order_class": str(order.order_class) if order.order_class else None,
            "status": str(order.status),
            "limit_price": float(order.limit_price) if order.limit_price else None,
            "stop_price": float(order.stop_price) if order.stop_price else None,
            "trail_price": float(order.trail_price) if order.trail_price else None,
            "trail_percent": float(order.trail_percent) if order.trail_percent else None,
            "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
        }
        # Include nested legs for multi-leg and bracket orders
        if getattr(order, "legs", None):
            result["legs"] = [cls._format_order_response(leg) for leg in order.legs]
        return result

    # ── Core order submission ─────────────────────────────────────

    def _submit_order(
        self,
        account_id: str,
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
        time_in_force: str = "day",
    ) -> Dict:
        """Submit an order for a specific user account. Type inferred from params."""
        tif = self._parse_time_in_force(time_in_force)
        oc = self._parse_order_class(order_class)

        tp_req = TakeProfitRequest(limit_price=take_profit) if take_profit else None
        sl_req = StopLossRequest(stop_price=stop_loss, limit_price=stop_loss_limit) if stop_loss else None

        common = dict(
            symbol=symbol, qty=qty, notional=notional, side=side,
            time_in_force=tif, order_class=oc,
            take_profit=tp_req, stop_loss=sl_req,
        )

        try:
            if trail_price is not None or trail_percent is not None:
                order_data = TrailingStopOrderRequest(
                    **common, trail_price=trail_price, trail_percent=trail_percent,
                )
            elif stop_price and limit_price:
                order_data = StopLimitOrderRequest(
                    **common, stop_price=stop_price, limit_price=limit_price,
                )
            elif stop_price:
                order_data = StopOrderRequest(**common, stop_price=stop_price)
            elif limit_price:
                order_data = LimitOrderRequest(**common, limit_price=limit_price)
            else:
                order_data = MarketOrderRequest(**common)

            # KEY DIFFERENCE: submit_order_for_account
            order = self.client.submit_order_for_account(
                account_id=account_id,
                order_data=order_data,
            )
            return self._format_order_response(order)

        except Exception as e:
            action = "buy" if side == OrderSide.BUY else "sell"
            raise Exception(f"Failed to {action} {symbol} for account {account_id}: {str(e)}")

    # ── Buy / Sell ────────────────────────────────────────────────

    def buy(
        self,
        account_id: str,
        symbol: str,
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
        time_in_force: str = "day",
    ) -> Dict:
        """Buy an asset for a user. Order type is inferred from parameters."""
        return self._submit_order(
            account_id=account_id, symbol=symbol, side=OrderSide.BUY,
            qty=qty, notional=notional, limit_price=limit_price,
            stop_price=stop_price, trail_price=trail_price,
            trail_percent=trail_percent, take_profit=take_profit,
            stop_loss=stop_loss, stop_loss_limit=stop_loss_limit,
            order_class=order_class, time_in_force=time_in_force,
        )

    def sell(
        self,
        account_id: str,
        symbol: str,
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
        time_in_force: str = "day",
    ) -> Dict:
        """Sell an asset for a user. Same params as buy()."""
        return self._submit_order(
            account_id=account_id, symbol=symbol, side=OrderSide.SELL,
            qty=qty, notional=notional, limit_price=limit_price,
            stop_price=stop_price, trail_price=trail_price,
            trail_percent=trail_percent, take_profit=take_profit,
            stop_loss=stop_loss, stop_loss_limit=stop_loss_limit,
            order_class=order_class, time_in_force=time_in_force,
        )

    # ── Replace Order ─────────────────────────────────────────────

    def replace_order(
        self,
        account_id: str,
        order_id: str,
        qty: Optional[int] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail: Optional[float] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict:
        """Modify an existing open order for an account."""
        tif = self._parse_time_in_force(time_in_force) if time_in_force else None
        try:
            order = self.client.replace_order_for_account_by_id(
                account_id=account_id,
                order_id=order_id,
                order_data=ReplaceOrderRequest(
                    qty=qty, limit_price=limit_price, stop_price=stop_price,
                    trail=trail, time_in_force=tif,
                ),
            )
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed to replace order {order_id}: {str(e)}")

    # ── Get Order by ID ───────────────────────────────────────────

    def get_order_by_id(
        self, account_id: str, order_id: str, nested: bool = True,
    ) -> Dict:
        """Retrieve a specific order by UUID. Set nested=True for leg details."""
        try:
            order = self.client.get_order_for_account_by_id(
                account_id=account_id,
                order_id=order_id,
                filter=GetOrderByIdRequest(nested=nested),
            )
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed to get order {order_id}: {str(e)}")

    # ── Orders Query ──────────────────────────────────────────────

    def get_orders(self, account_id: str, status: str = "open") -> List[Dict]:
        """Get orders for an account filtered by status ('open', 'closed', 'all')."""
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL,
        }
        query_status = status_map.get(status.lower(), QueryOrderStatus.OPEN)
        try:
            orders = self.client.get_orders_for_account(
                account_id=account_id,
                filter=GetOrdersRequest(status=query_status),
            )
            return [
                {
                    "id": str(order.id),
                    "symbol": order.symbol,
                    "qty": float(order.qty) if order.qty else None,
                    "side": str(order.side),
                    "type": str(order.order_type),
                    "status": str(order.status),
                    "limit_price": float(order.limit_price) if order.limit_price else None,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "submitted_at": str(order.submitted_at) if order.submitted_at else None,
                    "filled_at": str(order.filled_at) if order.filled_at else None,
                }
                for order in orders
            ]
        except Exception as e:
            raise Exception(f"Failed to get orders for {account_id}: {str(e)}")

    # ── Cancel Orders ─────────────────────────────────────────────

    def cancel_order(self, account_id: str, order_id: str) -> None:
        """Cancel a specific order for an account."""
        try:
            self.client.cancel_order_for_account_by_id(
                account_id=account_id, order_id=order_id,
            )
        except Exception as e:
            raise Exception(f"Failed to cancel order {order_id}: {str(e)}")

    def cancel_all_orders(self, account_id: str) -> None:
        """Cancel all open orders for an account."""
        try:
            self.client.cancel_orders_for_account(account_id=account_id)
        except Exception as e:
            raise Exception(f"Failed to cancel all orders for {account_id}: {str(e)}")

    # ── Positions ─────────────────────────────────────────────────

    def get_positions(self, account_id: str) -> List[Dict]:
        """Get all open positions for an account."""
        try:
            positions = self.client.get_all_positions_for_account(account_id=account_id)
            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                    "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
                    "side": str(pos.side),
                }
                for pos in positions
            ]
        except Exception as e:
            raise Exception(f"Failed to get positions for {account_id}: {str(e)}")

    def get_position(self, account_id: str, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol in a user's account."""
        try:
            pos = self.client.get_open_position_for_account(
                account_id=account_id, symbol_or_asset_id=symbol,
            )
            return {
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "avg_entry_price": float(pos.avg_entry_price),
                "market_value": float(pos.market_value),
                "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
                "side": str(pos.side),
            }
        except Exception:
            return None

    # ── Close Positions ───────────────────────────────────────────

    def close_position(
        self,
        account_id: str,
        symbol: str,
        qty: Optional[float] = None,
        percentage: Optional[float] = None,
    ) -> Dict:
        """Close a position fully or partially. Omit both qty and percentage for a full close."""
        close_options = None
        if qty is not None and percentage is not None:
            raise ValueError("Provide qty or percentage, not both.")
        if qty is not None:
            close_options = ClosePositionRequest(qty=str(qty))
        elif percentage is not None:
            close_options = ClosePositionRequest(percentage=str(percentage))

        try:
            order = self.client.close_position_for_account(
                account_id=account_id,
                symbol_or_asset_id=symbol,
                close_options=close_options,
            )
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed to close {symbol} for {account_id}: {str(e)}")

    def close_all_positions(self, account_id: str, cancel_orders: bool = True) -> List[Dict]:
        """Close all positions for a user account."""
        try:
            orders = self.client.close_all_positions_for_account(
                account_id=account_id, cancel_orders=cancel_orders,
            )
            return [self._format_order_response(o) for o in orders]
        except Exception as e:
            raise Exception(f"Failed to close all positions for {account_id}: {str(e)}")

    # ── Options Trading ───────────────────────────────────────────

    def exercise_options_position(self, account_id: str, symbol_or_contract_id: str) -> None:
        """Exercise a held options position for an account."""
        try:
            self.client.exercise_options_position_for_account_by_id(
                account_id=account_id,
                symbol_or_contract_id=symbol_or_contract_id,
            )
        except Exception as e:
            raise Exception(f"Failed to exercise option {symbol_or_contract_id}: {str(e)}")

    def submit_multi_leg_order(
        self,
        account_id: str,
        legs: List[Dict],
        qty: int,
        limit_price: Optional[float] = None,
        time_in_force: str = "day",
    ) -> Dict:
        """Submit a multi-leg option order (spreads, straddles, iron condors, etc.)."""
        tif = self._parse_time_in_force(time_in_force)

        leg_requests = []
        for leg in legs:
            side_str = leg.get("side")
            intent_str = leg.get("position_intent")
            side_enum = (
                {"buy": OrderSide.BUY, "sell": OrderSide.SELL}.get(side_str.lower())
                if side_str else None
            )
            intent_enum = self._parse_position_intent(intent_str)

            leg_requests.append(
                OptionLegRequest(
                    symbol=leg["symbol"],
                    ratio_qty=leg.get("ratio_qty", 1),
                    side=side_enum,
                    position_intent=intent_enum,
                )
            )

        common = dict(
            qty=qty, time_in_force=tif,
            order_class=OrderClass.MLEG, legs=leg_requests,
        )

        try:
            if limit_price is not None:
                order_data = LimitOrderRequest(**common, limit_price=limit_price)
            else:
                order_data = MarketOrderRequest(**common)

            order = self.client.submit_order_for_account(
                account_id=account_id,
                order_data=order_data,
            )
            return self._format_order_response(order)
        except Exception as e:
            raise Exception(f"Failed multi-leg order for {account_id}: {str(e)}")
