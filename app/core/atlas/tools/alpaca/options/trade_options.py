"""Options trading tool - buy or sell option contracts."""

from app.brokers.alpaca.broker import Alpaca
from typing import Literal, Optional
from app.core.atlas.tools.responses import success_response, error_response


def options_trade(
    position: Literal['buy', 'sell'],
    symbol: str,
    qty: int = 1,
    limit_price: Optional[float] = None,
    time_in_force: str = 'day',
) -> str:
    """Buy or sell an option contract by its OSI symbol."""
    alpaca = Alpaca()

    ops = {
        'buy': alpaca.buy_option,
        'sell': alpaca.sell_option,
    }

    handler = ops.get(position)
    if handler is None:
        return error_response(f"Invalid position: {position}")

    try:
        result = handler(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
            time_in_force=time_in_force,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to {position} option {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

OPTIONS_TRADE_DESCRIPTION = (
    "Buy or sell an option contract. Requires the full OSI symbol "
    "(e.g., 'SPY260320C00500000'). Use options_lookup or options_chain first "
    "to find the correct symbol. "
    "Example: options_trade(position='buy', symbol='SPY260320C00500000', qty=1)"
)

OPTIONS_TRADE_PARAMETERS = {
    "type": "object",
    "properties": {
        "position": {
            "type": "string",
            "enum": ["buy", "sell"],
            "description": "'buy' to open a long position, 'sell' to close or write."
        },
        "symbol": {
            "type": "string",
            "description": "The full OSI option symbol (e.g., 'SPY260320C00500000')."
        },
        "qty": {
            "type": "integer",
            "description": "Number of contracts.",
            "default": 1
        },
        "limit_price": {
            "type": "number",
            "description": "Limit price per contract. Omit for a market order."
        },
        "time_in_force": {
            "type": "string",
            "enum": ["day", "gtc", "ioc", "fok"],
            "description": "Time in force for the order.",
            "default": "day"
        }
    },
    "required": ["position", "symbol"],
    "additionalProperties": False
}

OPTIONS_TRADE_TOOL = {
    "name": "options_trade",
    "description": OPTIONS_TRADE_DESCRIPTION,
    "parameters": OPTIONS_TRADE_PARAMETERS,
    "function": options_trade,
}
