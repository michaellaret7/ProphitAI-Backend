"""Asset lookup tool - get info on a single asset or list all assets."""

from app.brokers.alpaca.broker import Alpaca
from typing import Optional
from app.core.atlas.tools.responses import success_response, error_response


def asset_lookup(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    asset_class: Optional[str] = None,
) -> str:
    """
    Look up asset information from Alpaca.

    If symbol is provided, returns detailed info for that single asset.
    Otherwise, returns a filtered list of all assets.
    """
    alpaca = Alpaca()

    try:
        if symbol:
            result = alpaca.get_asset(symbol)
        else:
            result = alpaca.get_all_assets(status=status, asset_class=asset_class)
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed asset lookup: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

ASSET_LOOKUP_DESCRIPTION = (
    "Look up asset information from Alpaca. Two modes:\n"
    "  - Single asset: Provide 'symbol' to get detailed info (tradable, shortable, "
    "fractionable, marginable, min_order_size, etc.).\n"
    "  - List assets: Omit 'symbol' and optionally filter by status and asset_class.\n"
    "Example: asset_lookup(symbol='AAPL')\n"
    "Example: asset_lookup(status='active', asset_class='us_equity')"
)

ASSET_LOOKUP_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Ticker symbol to look up (e.g., 'AAPL'). If provided, returns single asset details.",
        },
        "status": {
            "type": "string",
            "enum": ["active", "inactive"],
            "description": "(List mode) Filter by asset status.",
        },
        "asset_class": {
            "type": "string",
            "enum": ["us_equity", "us_option", "crypto"],
            "description": "(List mode) Filter by asset class.",
        },
    },
    "required": [],
    "additionalProperties": False,
}

ASSET_LOOKUP_TOOL = {
    "name": "asset_lookup",
    "description": ASSET_LOOKUP_DESCRIPTION,
    "parameters": ASSET_LOOKUP_PARAMETERS,
    "function": asset_lookup,
}
