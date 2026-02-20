"""Options discovery tools - find expirations and contracts for an underlying."""

from app.brokers.alpaca.broker import Alpaca
from typing import Literal, Optional, Tuple
from app.core.atlas.tools.responses import success_response, error_response


def options_lookup(
    operation: Literal['expirations', 'contracts'],
    underlying: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    expiration: Optional[str] = None,
    contract_type: Optional[str] = None,
    strike_min: Optional[float] = None,
    strike_max: Optional[float] = None,
    limit: Optional[int] = None,
) -> str:
    """Look up available option expirations or contracts for an underlying symbol."""
    alpaca = Alpaca()

    try:
        if operation == 'expirations':
            data = alpaca.get_option_expirations(
                underlying=underlying,
                start=start,
                end=end,
            )
            return success_response(data)

        strike_range: Optional[Tuple[float, float]] = None
        if strike_min is not None and strike_max is not None:
            strike_range = (strike_min, strike_max)

        data = alpaca.get_option_contracts(
            underlying=underlying,
            expiration=expiration,
            contract_type=contract_type,
            strike_range=strike_range,
            limit=limit,
        )
        return success_response(data)
    except Exception as e:
        return error_response(f"Failed options_lookup '{operation}' for {underlying}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

OPTIONS_LOOKUP_DESCRIPTION = (
    "Discover available option expirations or contracts for an underlying symbol. "
    "Two operations:\n"
    "  - 'expirations': List all available expiration dates. Optionally filter by start/end date range.\n"
    "  - 'contracts': List available OSI option symbols. Filter by expiration, contract_type ('call'/'put'), "
    "strike range (strike_min/strike_max), and limit.\n"
    "Example: options_lookup(operation='expirations', underlying='SPY')\n"
    "Example: options_lookup(operation='contracts', underlying='SPY', expiration='2026-03-20', contract_type='call', limit=20)"
)

OPTIONS_LOOKUP_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["expirations", "contracts"],
            "description": "'expirations' to list available dates, 'contracts' to list OSI symbols."
        },
        "underlying": {
            "type": "string",
            "description": "The underlying ticker symbol (e.g., 'SPY', 'AAPL')."
        },
        "start": {
            "type": "string",
            "description": "(expirations only) Earliest expiration date to include, 'YYYY-MM-DD'."
        },
        "end": {
            "type": "string",
            "description": "(expirations only) Latest expiration date to include, 'YYYY-MM-DD'."
        },
        "expiration": {
            "type": "string",
            "description": "(contracts only) Filter contracts to this expiration date, 'YYYY-MM-DD'."
        },
        "contract_type": {
            "type": "string",
            "enum": ["call", "put"],
            "description": "(contracts only) Filter by 'call' or 'put'."
        },
        "strike_min": {
            "type": "number",
            "description": "(contracts only) Minimum strike price."
        },
        "strike_max": {
            "type": "number",
            "description": "(contracts only) Maximum strike price."
        },
        "limit": {
            "type": "integer",
            "description": "(contracts only) Max number of contract symbols to return."
        }
    },
    "required": ["operation", "underlying"],
    "additionalProperties": False
}

OPTIONS_LOOKUP_TOOL = {
    "name": "options_lookup",
    "description": OPTIONS_LOOKUP_DESCRIPTION,
    "parameters": OPTIONS_LOOKUP_PARAMETERS,
    "function": options_lookup,
}
