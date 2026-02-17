"""Option snapshot tool - full snapshot (quote + trade + greeks) for option contracts."""

from app.utils.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def option_snapshot(symbol: str) -> str:
    """Fetch a full snapshot for an option contract."""
    alpaca = Alpaca()

    try:
        result = alpaca.get_option_snapshot(symbol)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to fetch option snapshot for {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

OPTION_SNAPSHOT_DESCRIPTION = (
    "Fetch a full snapshot for an option contract: latest quote (bid/ask), latest trade "
    "(price/size), and greeks (delta, gamma, theta, vega, rho).\n"
    "Example: option_snapshot(symbol='SPY260320C00580000')"
)

OPTION_SNAPSHOT_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Full OSI option symbol (e.g., 'SPY260320C00580000').",
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

OPTION_SNAPSHOT_TOOL = {
    "name": "option_snapshot",
    "description": OPTION_SNAPSHOT_DESCRIPTION,
    "parameters": OPTION_SNAPSHOT_PARAMETERS,
    "function": option_snapshot,
}
