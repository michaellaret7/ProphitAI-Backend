from app.utils.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def close_position(symbol: str) -> str:
    """Close an open position for the given symbol."""
    alpaca = Alpaca()

    try:
        result = alpaca.close_position(symbol)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to close position for {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

CLOSE_POSITION_DESCRIPTION = (
    "Close an open position for a given ticker symbol. "
    "Liquidates the entire position (all shares/units). "
    "Example: close_position(symbol='AAPL')"
)

CLOSE_POSITION_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "The ticker symbol of the position to close (e.g., 'AAPL')."
        }
    },
    "required": ["symbol"],
    "additionalProperties": False
}

CLOSE_POSITION_TOOL = {
    "name": "close_position",
    "description": CLOSE_POSITION_DESCRIPTION,
    "parameters": CLOSE_POSITION_PARAMETERS,
    "function": close_position,
}
