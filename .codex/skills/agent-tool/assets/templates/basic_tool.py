"""
[TOOL_NAME] - Brief description of the tool.

This tool provides [functionality description].
"""

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from typing import Annotated


# ================================
# --> Helper funcs
# ================================


# ================================
# --> Tools
# ================================

@agent_tool(name="tool_name")
def tool_name(
    ticker: str,
    lookback_days: Annotated[int, Param(min_val=30, max_val=756)] = 252,
) -> str:
    """
    Brief description of what the tool does.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        lookback_days: Historical lookback period in trading days

    Returns:
        Dict with ticker and processed result

    Examples:
        tool_name(ticker="AAPL", lookback_days=126)
        >>> {"success": True, "data": {"ticker": "AAPL", "lookback_days": 126, "processed": "Processed: AAPL"}}

    Raises:
        Exception: If ticker data cannot be retrieved
    """
    try:
        # =====================================================================
        # CORE TOOL LOGIC HERE
        # =====================================================================
        result = {
            "ticker": ticker,
            "lookback_days": lookback_days,
            "processed": f"Processed: {ticker}",
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Error in tool_name: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    # Test with required param only
    print("Test 1: Required param only")
    print(tool_name(ticker="AAPL"))
    print()

    # Test with all params
    print("Test 2: All params")
    print(tool_name(ticker="MSFT", lookback_days=126))
    print()

    # Test validation error
    print("Test 3: Validation error (empty string)")
    print(tool_name(ticker=""))
