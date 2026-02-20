"""Replace/modify an existing open order tool."""

from app.brokers.alpaca.broker import Alpaca
from typing import Optional
from app.core.atlas.tools.responses import success_response, error_response


def replace_order(
    order_id: str,
    qty: Optional[int] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    trail: Optional[float] = None,
    time_in_force: Optional[str] = None,
) -> str:
    """Modify an existing open order on Alpaca."""
    alpaca = Alpaca()

    try:
        result = alpaca.replace_order(
            order_id=order_id,
            qty=qty,
            limit_price=limit_price,
            stop_price=stop_price,
            trail=trail,
            time_in_force=time_in_force,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to replace order {order_id}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

REPLACE_ORDER_DESCRIPTION = (
    "Modify an existing open order. You can change qty, limit_price, stop_price, "
    "trail value (for trailing stops), or time_in_force. At least one field must be provided.\n"
    "Note: qty must be an integer (no fractional). The trail field updates whichever "
    "trail type (price or percent) was originally set on the order.\n"
    "Example: replace_order(order_id='abc-123', qty=50, limit_price=155.00)\n"
    "Example: replace_order(order_id='abc-123', trail=3.50)"
)

REPLACE_ORDER_PARAMETERS = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "description": "The Alpaca order UUID to modify.",
        },
        "qty": {
            "type": "integer",
            "description": "New quantity (integer only, no fractional shares).",
        },
        "limit_price": {
            "type": "number",
            "description": "New limit price (for limit/stop-limit orders).",
        },
        "stop_price": {
            "type": "number",
            "description": "New stop trigger price (for stop/stop-limit orders).",
        },
        "trail": {
            "type": "number",
            "description": "New trail value for trailing stop orders (updates original trail type).",
        },
        "time_in_force": {
            "type": "string",
            "enum": ["day", "gtc", "ioc", "fok", "opg", "cls"],
            "description": "New time in force value.",
        },
    },
    "required": ["order_id"],
    "additionalProperties": False,
}

REPLACE_ORDER_TOOL = {
    "name": "replace_order",
    "description": REPLACE_ORDER_DESCRIPTION,
    "parameters": REPLACE_ORDER_PARAMETERS,
    "function": replace_order,
}
