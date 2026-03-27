"""Watchlist retrieval tool.

Provides a tool for fetching a user's watchlist by UUID, returning
the watchlist name and all items with their tickers and inception prices.
"""

import uuid

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.repositories.user import get_watchlist_by_id


# ================================
# --> Tools
# ================================

@agent_tool(name="get_watchlist", category="portfolio")
def get_watchlist(watchlist_id: str) -> str:
    """Fetch a watchlist by its UUID and return all items.

Returns the watchlist name, creation date, and every ticker in the watchlist
with the price captured when the ticker was added.

**WHEN TO USE:**
- Retrieving the contents of a specific watchlist for analysis
- Getting the list of tickers to feed into portfolio tools
- Checking what tickers a user is tracking and their inception prices

**IMPORTANT:**
- watchlist_id must be a valid UUID string
- Returns None-safe: if watchlist doesn't exist, returns a clear error
- price_on_inception is the price when the ticker was added (for gain/loss tracking)

    Args:
        watchlist_id: UUID of the watchlist to retrieve (e.g., '550e8400-e29b-41d4-a716-446655440000')

    Returns:
        YAML-formatted watchlist data:
        - name: Watchlist name
        - creation_date: When the watchlist was created
        - updated_date: When the watchlist was last modified
        - ticker_count: Number of tickers in the watchlist
        - tickers: List of ticker symbols (convenience field for piping into portfolio tools)
        - items: List of {ticker, price_on_inception, added_at}

    Examples:
        get_watchlist(watchlist_id="550e8400-e29b-41d4-a716-446655440000")
        >>> {"success": True, "data": {"name": "Tech Growth", "tickers": ["AAPL", "MSFT"], ...}}

    Raises:
        ValueError: If watchlist_id is not a valid UUID or watchlist not found
    """
    try:
        if not watchlist_id or not watchlist_id.strip():
            return error_response("watchlist_id cannot be empty")

        # Reason: validate UUID format before hitting the DB to avoid leaking SQL errors
        try:
            uuid.UUID(watchlist_id.strip())
        except ValueError:
            return error_response(f"Invalid UUID format: {watchlist_id}")

        watchlist = get_watchlist_by_id(watchlist_id.strip())

        if watchlist is None:
            return error_response(f"Watchlist not found for id: {watchlist_id}")

        items = watchlist.get("items", [])
        tickers = [item["ticker"] for item in items]

        return success_response({
            "name": watchlist["name"],
            "creation_date": watchlist.get("creation_date"),
            "updated_date": watchlist.get("updated_date"),
            "ticker_count": len(tickers),
            "tickers": tickers,
            "items": items,
        })

    except Exception as e:
        return error_response(f"Failed to fetch watchlist: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_watchlist(watchlist_id="test-uuid-here"))
