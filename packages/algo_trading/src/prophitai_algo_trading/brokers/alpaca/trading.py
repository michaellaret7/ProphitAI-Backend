"""Alpaca order execution — submission, cancellation, replacement.

Thin adapter over ``alpaca.trading.client.TradingClient.submit_order`` /
``cancel_order_by_id`` / ``replace_order_by_id`` / etc. Order type is
inferred from the parameter set passed to ``_submit_order``:
trailing-stop > stop-limit > stop > limit > market.
"""

from __future__ import annotations

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, PositionIntent, TimeInForce
from alpaca.trading.requests import (
    ClosePositionRequest,
    GetOrderByIdRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    OptionLegRequest,
    ReplaceOrderRequest,
    StopLimitOrderRequest,
    StopLossRequest,
    StopOrderRequest,
    TakeProfitRequest,
    TrailingStopOrderRequest,
)


#     ================================
# --> Helper funcs
#     ================================

_TIME_IN_FORCE_MAP = {
    "day": TimeInForce.DAY,
    "gtc": TimeInForce.GTC,
    "ioc": TimeInForce.IOC,
    "fok": TimeInForce.FOK,
    "opg": TimeInForce.OPG,
    "cls": TimeInForce.CLS,
}

_ORDER_CLASS_MAP = {
    "simple": OrderClass.SIMPLE,
    "bracket": OrderClass.BRACKET,
    "oco": OrderClass.OCO,
    "oto": OrderClass.OTO,
    "mleg": OrderClass.MLEG,
}

_POSITION_INTENT_MAP = {
    "buy_to_open": PositionIntent.BUY_TO_OPEN,
    "buy_to_close": PositionIntent.BUY_TO_CLOSE,
    "sell_to_open": PositionIntent.SELL_TO_OPEN,
    "sell_to_close": PositionIntent.SELL_TO_CLOSE,
}


def _parse_time_in_force(time_in_force: str) -> TimeInForce:
    return _TIME_IN_FORCE_MAP.get(time_in_force.lower(), TimeInForce.DAY)


def _parse_order_class(order_class: str | None) -> OrderClass | None:
    if not order_class:
        return None

    result = _ORDER_CLASS_MAP.get(order_class.lower())

    if result is None:
        raise ValueError(
            f"Invalid order_class '{order_class}'. Must be: "
            "simple, bracket, oco, oto, mleg",
        )

    return result


def _parse_position_intent(intent: str | None) -> PositionIntent | None:
    if not intent:
        return None

    result = _POSITION_INTENT_MAP.get(intent.lower())

    if result is None:
        raise ValueError(
            f"Invalid position_intent '{intent}'. Must be: "
            "buy_to_open, buy_to_close, sell_to_open, sell_to_close",
        )

    return result


def _format_order_response(order) -> dict:
    """Format an Alpaca order object into a flat dict.

    Recurses into nested legs so multi-leg and bracket orders surface
    their child fills in the same shape as the parent.
    """
    result = {
        "id": str(order.id),
        "symbol": order.symbol,
        "qty": float(order.qty) if order.qty else None,
        "notional": float(order.notional) if order.notional else None,
        "side": order.side,
        "type": order.order_type,
        "order_class": order.order_class,
        "status": order.status,
        "limit_price": float(order.limit_price) if order.limit_price else None,
        "stop_price": float(order.stop_price) if order.stop_price else None,
        "trail_price": float(order.trail_price) if order.trail_price else None,
        "trail_percent": float(order.trail_percent) if order.trail_percent else None,
        "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
        "filled_avg_price": (
            float(order.filled_avg_price) if order.filled_avg_price else None
        ),
    }

    if getattr(order, "legs", None):
        result["legs"] = [_format_order_response(leg) for leg in order.legs]

    return result


def _is_crypto(symbol: str) -> bool:
    """Detect Alpaca crypto pairs by symbol shape (e.g. ``BTCUSD`` / ``ETH/USD``)."""
    cleaned = symbol.replace("/", "").upper()

    return cleaned.endswith("USD") and len(cleaned) in (6, 7, 8)


#     ================================
# --> Public service
#     ================================

class AlpacaTrading:
    """Order execution surface for the Alpaca trading API."""

    def __init__(self, client: TradingClient):
        self.client = client

    def _submit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float | None = None,
        notional: float | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trail_price: float | None = None,
        trail_percent: float | None = None,
        take_profit: float | None = None,
        stop_loss: float | None = None,
        stop_loss_limit: float | None = None,
        order_class: str | None = None,
        time_in_force: str = "day",
    ) -> dict:
        """Submit an order, inferring the type from the parameters provided."""
        # Reason: Alpaca crypto orders only support 'gtc' time-in-force
        if _is_crypto(symbol) and time_in_force == "day":
            time_in_force = "gtc"

        tif = _parse_time_in_force(time_in_force)
        oc = _parse_order_class(order_class)

        tp_req = TakeProfitRequest(limit_price=take_profit) if take_profit else None
        sl_req = (
            StopLossRequest(stop_price=stop_loss, limit_price=stop_loss_limit)
            if stop_loss
            else None
        )

        common = dict(
            symbol=symbol,
            qty=qty,
            notional=notional,
            side=side,
            time_in_force=tif,
            order_class=oc,
            take_profit=tp_req,
            stop_loss=sl_req,
        )

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

        order = self.client.submit_order(order_data=order_data)

        return _format_order_response(order)

    def buy(self, symbol: str, **kwargs) -> dict:
        """Buy ``symbol``. See ``_submit_order`` for keyword arguments."""
        return self._submit_order(symbol=symbol, side=OrderSide.BUY, **kwargs)

    def sell(self, symbol: str, **kwargs) -> dict:
        """Sell ``symbol``. See ``_submit_order`` for keyword arguments."""
        return self._submit_order(symbol=symbol, side=OrderSide.SELL, **kwargs)

    def close_position(
        self,
        symbol: str,
        qty: float | None = None,
        percentage: float | None = None,
    ) -> dict:
        """Close a position fully or partially.

        Provide ``qty`` or ``percentage`` for partial close, neither for full.
        """
        if qty is not None and percentage is not None:
            raise ValueError("Provide qty or percentage, not both.")

        close_options = None

        if qty is not None:
            close_options = ClosePositionRequest(qty=str(qty))
        elif percentage is not None:
            close_options = ClosePositionRequest(percentage=str(percentage))

        order = self.client.close_position(symbol, close_options=close_options)

        return {
            "id": str(order.id),
            "symbol": order.symbol,
            "qty": float(order.qty) if order.qty else None,
            "status": order.status,
        }

    def close_all_positions(self, cancel_orders: bool = True) -> list[dict]:
        """Close all positions; optionally cancel open orders first."""
        orders = self.client.close_all_positions(cancel_orders=cancel_orders)

        return [
            {"id": str(o.id), "symbol": o.symbol, "status": o.status}
            for o in orders
        ]

    def cancel_order(self, order_id: str) -> None:
        """Cancel a specific order by ID."""
        self.client.cancel_order_by_id(order_id)

    def cancel_all_orders(self) -> None:
        """Cancel every open order on the account."""
        self.client.cancel_orders()

    def replace_order(
        self,
        order_id: str,
        qty: int | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trail: float | None = None,
        time_in_force: str | None = None,
    ) -> dict:
        """Modify an existing open order."""
        tif = _parse_time_in_force(time_in_force) if time_in_force else None

        order = self.client.replace_order_by_id(
            order_id=order_id,
            order_data=ReplaceOrderRequest(
                qty=qty,
                limit_price=limit_price,
                stop_price=stop_price,
                trail=trail,
                time_in_force=tif,
            ),
        )

        return _format_order_response(order)

    def get_order_by_id(self, order_id: str, nested: bool = True) -> dict:
        """Retrieve a specific order by UUID; ``nested`` includes leg detail."""
        order = self.client.get_order_by_id(
            order_id=order_id,
            filter=GetOrderByIdRequest(nested=nested),
        )

        return _format_order_response(order)

    def exercise_options_position(self, symbol_or_contract_id: str) -> None:
        """Exercise a held options position (OSI symbol or contract UUID)."""
        self.client.exercise_options_position(
            symbol_or_contract_id=symbol_or_contract_id,
        )

    def submit_multi_leg_order(
        self,
        legs: list[dict],
        qty: int,
        limit_price: float | None = None,
        time_in_force: str = "day",
    ) -> dict:
        """Submit a multi-leg option order (spreads, straddles, condors, etc.)."""
        tif = _parse_time_in_force(time_in_force)

        leg_requests = []

        for leg in legs:
            side_str = leg.get("side")
            intent_str = leg.get("position_intent")

            side_enum = (
                {"buy": OrderSide.BUY, "sell": OrderSide.SELL}.get(side_str.lower())
                if side_str
                else None
            )
            intent_enum = _parse_position_intent(intent_str)

            leg_requests.append(
                OptionLegRequest(
                    symbol=leg["symbol"],
                    ratio_qty=leg.get("ratio_qty", 1),
                    side=side_enum,
                    position_intent=intent_enum,
                ),
            )

        common = dict(
            qty=qty,
            time_in_force=tif,
            order_class=OrderClass.MLEG,
            legs=leg_requests,
        )

        if limit_price is not None:
            order_data = LimitOrderRequest(**common, limit_price=limit_price)
        else:
            order_data = MarketOrderRequest(**common)

        order = self.client.submit_order(order_data=order_data)

        return _format_order_response(order)
