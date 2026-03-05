"""Option price history tool — OHLCV bars for a specific contract."""

from typing import Annotated, Literal, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response


# ================================
# --> Tools
# ================================

@agent_tool(name="get_option_price_history")
def get_option_price_history(
    osi_symbol: str,
    timeframe: Literal["1min", "1h", "1d", "1w", "1m"] = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Annotated[int, Param(min_val=1, max_val=500)] = 30,
) -> str:
    """
    Get OHLCV price history bars for a specific option contract.

    Provide the OSI symbol from get_option_contracts or get_options_chain.
    Returns timestamped bars with open, high, low, close, volume, and VWAP.

    Args:
        osi_symbol: OSI option symbol (e.g., 'AAPL260619C00200000')
        timeframe: Bar timeframe - '1min', '1h', '1d', '1w', or '1m'
        start: Start date/datetime ISO string (YYYY-MM-DD)
        end: End date/datetime ISO string (YYYY-MM-DD)
        limit: Maximum number of bars to return

    Returns:
        List of OHLCV bars with timestamp, open, high, low, close, volume, vwap

    Examples:
        get_option_price_history(osi_symbol="AAPL260619C00200000", timeframe="1d", limit=10)
        >>> {"success": True, "data": {"symbol": "AAPL260619C00200000", "bars": [...]}}
    """
    osi_symbol = osi_symbol.upper().strip()

    try:
        from app.repositories.options import get_options_repo
        repo = get_options_repo()

        bars = repo.get_option_bars(
            symbol=osi_symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=limit,
        )

        return success_response({
            "symbol": osi_symbol,
            "timeframe": timeframe,
            "count": len(bars),
            "bars": bars,
        })
    except Exception as e:
        return error_response(f"Failed to fetch price history for {osi_symbol}: {e}")
