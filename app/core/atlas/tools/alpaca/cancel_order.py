from app.utils.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def cancel_order(order_id: str) -> str:
    """Cancel an open order by its ID."""
    alpaca = Alpaca()

    try:
        alpaca.cancel_order(order_id)
        return success_response(f"Order {order_id} cancelled.")
    except Exception as e:
        return error_response(f"Failed to cancel order {order_id}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

CANCEL_ORDER_DESCRIPTION = (
    "Cancel an open order by its order ID. "
    "Use this when you need to cancel a pending or partially filled order. "
    "Example: cancel_order(order_id='b5765e8a-5b2c-4b7a-9f1a-3c8d2e4f6a8b')"
)

CANCEL_ORDER_PARAMETERS = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "description": "The Alpaca order ID to cancel."
        }
    },
    "required": ["order_id"],
    "additionalProperties": False
}

CANCEL_ORDER_TOOL = {
    "name": "cancel_order",
    "description": CANCEL_ORDER_DESCRIPTION,
    "parameters": CANCEL_ORDER_PARAMETERS,
    "function": cancel_order,
}
