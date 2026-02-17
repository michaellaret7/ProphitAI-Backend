"""Options chain tool - fetch quotes and greeks for an underlying."""

from app.utils.alpaca.broker import Alpaca
from typing import Optional
from app.core.atlas.tools.responses import success_response, error_response


def options_chain(
    underlying: str,
    expiration: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """Fetch the options chain (quotes + greeks) for an underlying symbol."""
    alpaca = Alpaca()

    try:
        data = alpaca.get_options_chain(
            underlying=underlying,
            expiration=expiration,
            limit=limit,
            return_df=False,
        )
        return success_response(data)
    except Exception as e:
        return error_response(f"Failed to fetch options chain for {underlying}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

OPTIONS_CHAIN_DESCRIPTION = (
    "Fetch the full options chain for an underlying symbol with quotes and greeks. "
    "Returns per-contract data: symbol, expiration, strike, type, bid, ask, mid, last, "
    "delta, gamma, theta, vega, and implied volatility. "
    "Use options_lookup first to find valid expirations, then pass one here. "
    "Example: options_chain(underlying='SPY', expiration='2026-03-20', limit=50)"
)

OPTIONS_CHAIN_PARAMETERS = {
    "type": "object",
    "properties": {
        "underlying": {
            "type": "string",
            "description": "The underlying ticker symbol (e.g., 'SPY', 'AAPL')."
        },
        "expiration": {
            "type": "string",
            "description": "Filter to a specific expiration date, 'YYYY-MM-DD'. Recommended for focused results."
        },
        "limit": {
            "type": "integer",
            "description": "Max number of contracts to return."
        }
    },
    "required": ["underlying"],
    "additionalProperties": False
}

OPTIONS_CHAIN_TOOL = {
    "name": "options_chain",
    "description": OPTIONS_CHAIN_DESCRIPTION,
    "parameters": OPTIONS_CHAIN_PARAMETERS,
    "function": options_chain,
}
