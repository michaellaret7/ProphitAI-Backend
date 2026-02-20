"""Multi-leg option order tool - spreads, straddles, iron condors, etc."""

from app.brokers.alpaca.broker import Alpaca
from typing import Optional, List, Dict
from app.core.atlas.tools.responses import success_response, error_response


def multi_leg_order(
    legs: List[Dict],
    qty: int,
    limit_price: Optional[float] = None,
    time_in_force: str = 'day',
) -> str:
    """Submit a multi-leg option order through Alpaca."""
    alpaca = Alpaca()

    try:
        result = alpaca.submit_multi_leg_order(
            legs=legs,
            qty=qty,
            limit_price=limit_price,
            time_in_force=time_in_force,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to submit multi-leg order: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

MULTI_LEG_ORDER_DESCRIPTION = (
    "Submit a multi-leg option order (spreads, straddles, iron condors, etc.). "
    "Each leg specifies an OSI option symbol, ratio_qty, and direction (side or position_intent). "
    "Use limit_price for net debit (positive) or net credit (negative). Omit for market.\n"
    "Examples:\n"
    "  Bull call spread: multi_leg_order(\n"
    "    legs=[{symbol:'AAPL260117C00200000', ratio_qty:1, side:'buy'},\n"
    "          {symbol:'AAPL260117C00220000', ratio_qty:1, side:'sell'}],\n"
    "    qty=1, limit_price=3.50)\n"
    "  Iron condor (4 legs): multi_leg_order(\n"
    "    legs=[{symbol:'SPY...P00450000', ratio_qty:1, position_intent:'buy_to_open'},\n"
    "          {symbol:'SPY...P00460000', ratio_qty:1, position_intent:'sell_to_open'},\n"
    "          {symbol:'SPY...C00500000', ratio_qty:1, position_intent:'sell_to_open'},\n"
    "          {symbol:'SPY...C00510000', ratio_qty:1, position_intent:'buy_to_open'}],\n"
    "    qty=1, limit_price=-2.00)"
)

MULTI_LEG_ORDER_PARAMETERS = {
    "type": "object",
    "properties": {
        "legs": {
            "type": "array",
            "description": "2–4 option legs for the spread.",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Full OSI option symbol (e.g., 'AAPL260117C00200000').",
                    },
                    "ratio_qty": {
                        "type": "number",
                        "description": "Proportional qty relative to parent qty. Default 1.",
                        "default": 1,
                    },
                    "side": {
                        "type": "string",
                        "enum": ["buy", "sell"],
                        "description": "'buy' or 'sell'. Provide side or position_intent.",
                    },
                    "position_intent": {
                        "type": "string",
                        "enum": ["buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"],
                        "description": "Explicit intent. Provide side or position_intent.",
                    },
                },
                "required": ["symbol"],
            },
            "minItems": 2,
            "maxItems": 4,
        },
        "qty": {
            "type": "integer",
            "description": "Number of contracts for the whole spread.",
        },
        "limit_price": {
            "type": "number",
            "description": "Net debit (positive) or net credit (negative). Omit for market order.",
        },
        "time_in_force": {
            "type": "string",
            "enum": ["day", "gtc", "ioc", "fok"],
            "description": "Time in force for the order.",
            "default": "day",
        },
    },
    "required": ["legs", "qty"],
    "additionalProperties": False,
}

MULTI_LEG_ORDER_TOOL = {
    "name": "multi_leg_order",
    "description": MULTI_LEG_ORDER_DESCRIPTION,
    "parameters": MULTI_LEG_ORDER_PARAMETERS,
    "function": multi_leg_order,
}
