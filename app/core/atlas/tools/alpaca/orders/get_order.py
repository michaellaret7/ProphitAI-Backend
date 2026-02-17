"""Get order by ID tool - retrieve a specific order's details."""

from app.utils.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def get_order(order_id: str, nested: bool = True) -> str:
    """Retrieve a specific order by its UUID."""
    alpaca = Alpaca()

    try:
        result = alpaca.get_order_by_id(order_id, nested=nested)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to get order {order_id}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

GET_ORDER_DESCRIPTION = (
    "Retrieve a specific order by its UUID. Returns full order details including "
    "status, fill info, and nested leg details for bracket/multi-leg orders.\n"
    "Example: get_order(order_id='b5765e8a-5b2c-4b7a-9f1a-3c8d2e4f6a8b')"
)

GET_ORDER_PARAMETERS = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "description": "The Alpaca order UUID to look up.",
        },
        "nested": {
            "type": "boolean",
            "description": "Include nested leg details for multi-leg/bracket orders. Defaults to true.",
            "default": True,
        },
    },
    "required": ["order_id"],
    "additionalProperties": False,
}

GET_ORDER_TOOL = {
    "name": "get_order",
    "description": GET_ORDER_DESCRIPTION,
    "parameters": GET_ORDER_PARAMETERS,
    "function": get_order,
}
