from app.brokers.alpaca.broker import Alpaca
from typing import Literal
from app.core.atlas.tools.responses import success_response, error_response

def alpaca_acct_and_portfolio(
    operation: Literal['account','positions', 'open_orders']
    ) -> str:
    """Retrieve Alpaca account info or portfolio data for the given operation."""

    alpaca = Alpaca()

    ops = {
        'account': alpaca.get_account,
        'positions': alpaca.get_positions,
        'open_orders': alpaca.get_orders,
        'cancel_all_orders': alpaca.cancel_all_orders,
        'close_all_positions': alpaca.close_all_positions,
    }

    handler = ops.get(operation)
    if handler is None:
        return error_response(f"Invalid operation: {operation}")

    try:
        return success_response(handler())
    except Exception as e:
        return error_response(f"Failed to execute '{operation}': {e}")

# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

ALPACA_ACCT_AND_PORTFOLIO_DESCRIPTION = (
    "Retrieve Alpaca account info or portfolio data. Operations:\n"
    "  - 'account': Full account details (buying power, cash, equity, etc.)\n"
    "  - 'positions': All currently open positions.\n"
    "  - 'open_orders': All open/pending orders.\n"
    "  - 'cancel_all_orders': Cancel every open order.\n"
    "  - 'close_all_positions': Liquidate all positions.\n"
    "Example: alpaca_acct_and_portfolio(operation='positions')"
)

ALPACA_ACCT_AND_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["account", "positions", "open_orders", "cancel_all_orders", "close_all_positions"],
            "description": "The account/portfolio operation to perform."
        }
    },
    "required": ["operation"],
    "additionalProperties": False
}

ALPACA_ACCT_AND_PORTFOLIO_TOOL = {
    "name": "alpaca_acct_and_portfolio",
    "description": ALPACA_ACCT_AND_PORTFOLIO_DESCRIPTION,
    "parameters": ALPACA_ACCT_AND_PORTFOLIO_PARAMETERS,
    "function": alpaca_acct_and_portfolio,
}


if __name__ == "__main__":
    print(alpaca_acct_and_portfolio('account'))
    print(alpaca_acct_and_portfolio('positions'))
    print(alpaca_acct_and_portfolio('open_orders'))