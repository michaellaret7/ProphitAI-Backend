"""Option bars tool - OHLCV history for option contracts."""

from app.utils.alpaca.broker import Alpaca
from typing import Optional
from app.core.atlas.tools.responses import success_response, error_response


def option_bars(
    symbol: str,
    timeframe: str = '1d',
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """Fetch OHLCV bars for an option contract."""
    alpaca = Alpaca()

    try:
        result = alpaca.get_option_bars(
            symbol=symbol, timeframe=timeframe, start=start, end=end, limit=limit,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to fetch option bars for {symbol}: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

OPTION_BARS_DESCRIPTION = (
    "Fetch OHLCV price bars for an option contract. Returns timestamp, open, high, low, "
    "close, volume, vwap, and trade_count per bar.\n"
    "Example: option_bars(symbol='SPY260320C00580000', timeframe='1d', limit=10)"
)

OPTION_BARS_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Full OSI option symbol (e.g., 'SPY260320C00580000').",
        },
        "timeframe": {
            "type": "string",
            "enum": ["1min", "1h", "1d", "1w", "1m"],
            "description": "Bar timeframe. Default '1d'.",
            "default": "1d",
        },
        "start": {
            "type": "string",
            "description": "Start date/datetime ISO string (e.g., '2026-02-01').",
        },
        "end": {
            "type": "string",
            "description": "End date/datetime ISO string (e.g., '2026-02-15').",
        },
        "limit": {
            "type": "integer",
            "description": "Max number of bars to return.",
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

OPTION_BARS_TOOL = {
    "name": "option_bars",
    "description": OPTION_BARS_DESCRIPTION,
    "parameters": OPTION_BARS_PARAMETERS,
    "function": option_bars,
}
