"""Close a position tool - full or partial by qty or percentage."""

from app.utils.alpaca.broker import Alpaca
from typing import Optional
from app.core.atlas.tools.responses import success_response, error_response


def close_position(
    symbol: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
) -> str:
    """Close an open position fully or partially."""
    alpaca = Alpaca()

    try:
        result = alpaca.close_position(symbol, qty=qty, percentage=percentage)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to close position for {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

CLOSE_POSITION_DESCRIPTION = (
    "Close an open position for a given ticker symbol. "
    "Omit both qty and percentage to liquidate the entire position. "
    "Provide qty for a specific number of shares, or percentage (0.0–1.0) for a fraction.\n"
    "Example (full close): close_position(symbol='AAPL')\n"
    "Example (close 50 shares): close_position(symbol='AAPL', qty=50)\n"
    "Example (close 25%): close_position(symbol='AAPL', percentage=0.25)"
)

CLOSE_POSITION_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "The ticker symbol of the position to close (e.g., 'AAPL').",
        },
        "qty": {
            "type": "number",
            "description": "Number of shares to close. Omit for full close. Mutually exclusive with percentage.",
        },
        "percentage": {
            "type": "number",
            "description": "Fraction of position to close, 0.0–1.0 (e.g., 0.5 = 50%). Mutually exclusive with qty.",
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

CLOSE_POSITION_TOOL = {
    "name": "close_position",
    "description": CLOSE_POSITION_DESCRIPTION,
    "parameters": CLOSE_POSITION_PARAMETERS,
    "function": close_position,
}
