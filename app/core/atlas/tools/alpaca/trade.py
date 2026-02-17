from app.utils.alpaca.broker import Alpaca
from typing import Literal, Optional
from app.core.atlas.tools.responses import success_response, error_response


def submit_trade(
    position: Literal['buy', 'sell'],
    symbol: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    time_in_force: str = 'day'
) -> str:
    """Submit a buy or sell order through Alpaca."""

    alpaca = Alpaca()

    ops = {
        'buy': alpaca.buy,
        'sell': alpaca.sell,
    }

    handler = ops.get(position)
    if handler is None:
        return error_response(f"Invalid position: {position}")

    try:
        result = handler(
            symbol=symbol,
            qty=qty,
            notional=notional,
            limit_price=limit_price,
            stop_price=stop_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            time_in_force=time_in_force,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to {position} {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

TRADE_DESCRIPTION = (
    "Submit a buy or sell equity order through Alpaca. "
    "Specify qty (shares) OR notional (dollar amount), not both. "
    "Omit limit_price and stop_price for a simple market order. "
    "Example: submit_trade(position='buy', symbol='AAPL', qty=10)\n"
    "Example: submit_trade(position='sell', symbol='MSFT', notional=500.0, limit_price=420.00)"
)

TRADE_PARAMETERS = {
    "type": "object",
    "properties": {
        "position": {
            "type": "string",
            "enum": ["buy", "sell"],
            "description": "'buy' or 'sell'."
        },
        "symbol": {
            "type": "string",
            "description": "Ticker symbol (e.g., 'AAPL')."
        },
        "qty": {
            "type": "number",
            "description": "Number of shares. Use this OR notional, not both."
        },
        "notional": {
            "type": "number",
            "description": "Dollar amount to trade. Use this OR qty, not both."
        },
        "limit_price": {
            "type": "number",
            "description": "Limit price. Omit for a market order."
        },
        "stop_price": {
            "type": "number",
            "description": "Stop price for stop/stop-limit orders."
        },
        "take_profit": {
            "type": "number",
            "description": "Take-profit price for bracket orders."
        },
        "stop_loss": {
            "type": "number",
            "description": "Stop-loss price for bracket orders."
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

TRADE_TOOL = {
    "name": "submit_trade",
    "description": TRADE_DESCRIPTION,
    "parameters": TRADE_PARAMETERS,
    "function": submit_trade,
}
