"""Close all open positions tool."""

from app.utils.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def close_all_positions() -> str:
    """Liquidate all open positions on the account."""
    alpaca = Alpaca()

    try:
        result = alpaca.close_all_positions(cancel_orders=True)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to close all positions: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

CLOSE_ALL_POSITIONS_DESCRIPTION = (
    "Liquidate every open position on the Alpaca account. "
    "Also cancels all open orders before closing. "
    "Takes no parameters. Use with caution. "
    "Example: close_all_positions()"
)

CLOSE_ALL_POSITIONS_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False
}

CLOSE_ALL_POSITIONS_TOOL = {
    "name": "close_all_positions",
    "description": CLOSE_ALL_POSITIONS_DESCRIPTION,
    "parameters": CLOSE_ALL_POSITIONS_PARAMETERS,
    "function": close_all_positions,
}
