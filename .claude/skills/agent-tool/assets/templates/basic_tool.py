"""
[TOOL_NAME] - Brief description of the tool.

This tool provides [functionality description].
"""

from app.core.atlas.tools.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
from typing import Optional


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def tool_name(
    ticker: str,
    lookback_days: Optional[int] = None,
    _simulation_date: str = None
) -> str:
    """
    Brief description of what the tool does.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        lookback_days: Historical lookback period (default: 252)
        _simulation_date: Optional simulation date (injected by agent framework)

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Result data when successful
            - 'error' (str): Error message when unsuccessful
    """
    # Validate inputs
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.optional_numeric('lookback_days', lookback_days, default=252, min_val=30, max_val=756)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    lookback_days = v.get('lookback_days')

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


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

TOOL_NAME_DESCRIPTION = (
    "Brief description for LLM. Explain what the tool does and when to use it. "
    "Include details about return values. "
    "Example: tool_name(ticker='AAPL', lookback_days=126)"
)

TOOL_NAME_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL')"
        },
        "lookback_days": {
            "type": "integer",
            "description": "Historical lookback period in trading days",
            "minimum": 30,
            "maximum": 756,
            "default": 252
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

TOOL_NAME_TOOL = {
    "name": "tool_name",
    "description": TOOL_NAME_DESCRIPTION,
    "parameters": TOOL_NAME_PARAMETERS,
    "function": tool_name,
}


# ==============================================================================
# STANDALONE TESTING
# ==============================================================================

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
