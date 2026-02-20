"""Option latest quote tool - real-time bid/ask for option contracts."""

from app.brokers.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def option_latest_quote(symbol: str) -> str:
    """Fetch the latest bid/ask quote for an option contract."""
    alpaca = Alpaca()

    try:
        result = alpaca.get_option_latest_quote(symbol)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to fetch option quote for {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

OPTION_LATEST_QUOTE_DESCRIPTION = (
    "Fetch the latest bid/ask quote for an option contract. Returns bid_price, bid_size, "
    "ask_price, ask_size, and timestamp.\n"
    "Example: option_latest_quote(symbol='SPY260320C00580000')"
)

OPTION_LATEST_QUOTE_PARAMETERS = {
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

OPTION_LATEST_QUOTE_TOOL = {
    "name": "option_latest_quote",
    "description": OPTION_LATEST_QUOTE_DESCRIPTION,
    "parameters": OPTION_LATEST_QUOTE_PARAMETERS,
    "function": option_latest_quote,
}
