"""Exercise an options position tool."""

from app.brokers.alpaca.broker import Alpaca
from app.core.atlas.tools.responses import success_response, error_response


def exercise_option(symbol_or_contract_id: str) -> str:
    """Exercise a held options position."""
    alpaca = Alpaca()

    try:
        alpaca.exercise_options_position(symbol_or_contract_id)
        return success_response(f"Successfully exercised option {symbol_or_contract_id}.")
    except Exception as e:
        return error_response(f"Failed to exercise option {symbol_or_contract_id}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

EXERCISE_OPTION_DESCRIPTION = (
    "Exercise a held options position. Converts the option into underlying shares "
    "at the strike price. You must hold the contract.\n"
    "Example: exercise_option(symbol_or_contract_id='SPY260320P00480000')"
)

EXERCISE_OPTION_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbol_or_contract_id": {
            "type": "string",
            "description": "The OSI option symbol (e.g., 'SPY260320P00480000') or contract UUID.",
        },
    },
    "required": ["symbol_or_contract_id"],
    "additionalProperties": False,
}

EXERCISE_OPTION_TOOL = {
    "name": "exercise_option",
    "description": EXERCISE_OPTION_DESCRIPTION,
    "parameters": EXERCISE_OPTION_PARAMETERS,
    "function": exercise_option,
}
