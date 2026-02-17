"""Submit equity/crypto trade tool."""

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
    trail_price: Optional[float] = None,
    trail_percent: Optional[float] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
    order_class: Optional[str] = None,
    time_in_force: str = 'day',
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
            trail_price=trail_price,
            trail_percent=trail_percent,
            take_profit=take_profit,
            stop_loss=stop_loss,
            stop_loss_limit=stop_loss_limit,
            order_class=order_class,
            time_in_force=time_in_force,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to {position} {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

TRADE_DESCRIPTION = (
    "Submit a buy or sell order through Alpaca. Supports market, limit, stop, "
    "stop-limit, and trailing stop orders. Use order_class for bracket/OCO/OTO orders.\n"
    "Order type is inferred from parameters:\n"
    "  - trail_price or trail_percent → trailing stop\n"
    "  - stop_price + limit_price → stop-limit\n"
    "  - stop_price only → stop\n"
    "  - limit_price only → limit\n"
    "  - none of the above → market\n"
    "Examples:\n"
    "  Market buy: submit_trade(position='buy', symbol='AAPL', qty=10)\n"
    "  Trailing stop sell: submit_trade(position='sell', symbol='AAPL', qty=10, trail_percent=2.0)\n"
    "  Bracket buy: submit_trade(position='buy', symbol='AAPL', qty=10, "
    "take_profit=160, stop_loss=140, order_class='bracket')"
)

TRADE_PARAMETERS = {
    "type": "object",
    "properties": {
        "position": {
            "type": "string",
            "enum": ["buy", "sell"],
            "description": "'buy' or 'sell'.",
        },
        "symbol": {
            "type": "string",
            "description": "Ticker symbol (e.g., 'AAPL') or crypto pair (e.g., 'BTC/USD').",
        },
        "qty": {
            "type": "number",
            "description": "Number of shares. Use this OR notional, not both.",
        },
        "notional": {
            "type": "number",
            "description": "Dollar amount to trade. Use this OR qty, not both.",
        },
        "limit_price": {
            "type": "number",
            "description": "Limit price. Creates a limit order (or stop-limit if stop_price also set).",
        },
        "stop_price": {
            "type": "number",
            "description": "Stop trigger price for stop/stop-limit orders.",
        },
        "trail_price": {
            "type": "number",
            "description": "Dollar offset for trailing stop. Mutually exclusive with trail_percent.",
        },
        "trail_percent": {
            "type": "number",
            "description": "Percent offset for trailing stop (e.g., 2.0 = 2%). Mutually exclusive with trail_price.",
        },
        "take_profit": {
            "type": "number",
            "description": "Take-profit limit price (exit leg). Required for bracket/OCO orders.",
        },
        "stop_loss": {
            "type": "number",
            "description": "Stop-loss trigger price (exit leg). Required for bracket/OCO orders.",
        },
        "stop_loss_limit": {
            "type": "number",
            "description": "Stop-loss limit price (exit leg). Omit for market-on-trigger.",
        },
        "order_class": {
            "type": "string",
            "enum": ["bracket", "oco", "oto"],
            "description": (
                "'bracket': entry + take_profit + stop_loss. "
                "'oco': one-cancels-other exit (both take_profit and stop_loss required). "
                "'oto': one-triggers-other (entry + one exit leg)."
            ),
        },
        "time_in_force": {
            "type": "string",
            "enum": ["day", "gtc", "ioc", "fok", "opg", "cls"],
            "description": "Time in force. 'opg' = market-on-open, 'cls' = market-on-close.",
            "default": "day",
        },
    },
    "required": ["position", "symbol"],
    "additionalProperties": False,
}

TRADE_TOOL = {
    "name": "submit_trade",
    "description": TRADE_DESCRIPTION,
    "parameters": TRADE_PARAMETERS,
    "function": submit_trade,
}
