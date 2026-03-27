"""Option expiration date discovery tool."""

from typing import Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response


# ================================
# --> Tools
# ================================

@agent_tool(name="get_option_expirations", category="options")
def get_option_expirations(
    underlying: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    include_expired: bool = False,
) -> str:
    """
    Get available option expiration dates for an underlying symbol.

    Use this to discover what expiration dates exist before looking up
    specific contracts or chains. Returns a sorted list of dates.

    Args:
        underlying: Underlying ticker symbol (e.g., 'AAPL', 'SPY')
        start: Earliest expiration date to include (YYYY-MM-DD, inclusive)
        end: Latest expiration date to include (YYYY-MM-DD, inclusive)
        include_expired: If True, include already-expired dates

    Returns:
        Sorted list of expiration dates in YYYY-MM-DD format

    Examples:
        get_option_expirations(underlying="AAPL")
        >>> {"success": True, "data": {"underlying": "AAPL", "expirations": ["2026-03-20", ...]}}
    """
    underlying = underlying.upper().strip()
    if not underlying:
        return error_response("underlying symbol is required")

    try:
        from prophitai_data.clients.options import get_options_repo
        repo = get_options_repo()

        dates = repo.get_available_dates(
            underlying=underlying,
            start=start,
            end=end,
            include_expired=include_expired,
        )

        return success_response({
            "underlying": underlying,
            "count": len(dates),
            "expirations": dates,
        })
    except Exception as e:
        return error_response(f"Failed to fetch expirations for {underlying}: {e}")
