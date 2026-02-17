"""Cancel all open orders tool."""

from app.utils.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def cancel_all_orders() -> str:
    """Cancel every open order on the account."""
    alpaca = Alpaca()

    try:
        alpaca.cancel_all_orders()
        return success_response("All open orders cancelled.")
    except Exception as e:
        return error_response(f"Failed to cancel all orders: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

CANCEL_ALL_ORDERS_DESCRIPTION = (
    "Cancel every open order on the Alpaca account. "
    "Takes no parameters. Use with caution. "
    "Example: cancel_all_orders()"
)

CANCEL_ALL_ORDERS_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False
}

CANCEL_ALL_ORDERS_TOOL = {
    "name": "cancel_all_orders",
    "description": CANCEL_ALL_ORDERS_DESCRIPTION,
    "parameters": CANCEL_ALL_ORDERS_PARAMETERS,
    "function": cancel_all_orders,
}
