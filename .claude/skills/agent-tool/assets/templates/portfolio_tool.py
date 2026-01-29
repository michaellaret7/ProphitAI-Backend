"""
[TOOL_NAME] - Portfolio analysis tool template.

This tool analyzes [aspect] of a portfolio.
"""

from app.core.atlas.tool_lib.common.responses import success_response, error_response
from app.core.atlas.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.utils.tool_validator import ToolValidator
from typing import Dict, Any, Optional


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def portfolio_tool_name(
    portfolio_dict: Optional[dict] = None,
    lookback_days: Optional[int] = None,
    _simulation_date: str = None
) -> str:
    """
    Analyze [aspect] of a portfolio.

    Args:
        portfolio_dict: Portfolio with ticker keys mapping to allocation/position values.
            Example: {'AAPL': {'allocation': 0.5, 'position': 'long'}, ...}
        lookback_days: Historical window for analysis (default: 252 trading days)
        _simulation_date: Optional simulation date (injected by agent framework)

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether analysis succeeded
            - 'data' (dict): Analysis results when successful
            - 'error' (str): Error message when unsuccessful
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.optional_numeric('lookback_days', lookback_days, default=252, min_val=30, max_val=756)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values (guaranteed non-None after validation)
    validated_portfolio: dict = v.get('portfolio_dict')
    validated_lookback: int = v.get('lookback_days')

    try:
        # =====================================================================
        # CORE ANALYSIS LOGIC HERE
        # =====================================================================

        # Extract holdings info
        tickers = list(validated_portfolio.keys())
        allocations = {t: h['allocation'] for t, h in validated_portfolio.items()}
        positions = {t: h['position'] for t, h in validated_portfolio.items()}

        # Calculate metrics
        total_long = sum(a for t, a in allocations.items() if positions[t] == 'long')
        total_short = sum(a for t, a in allocations.items() if positions[t] == 'short')

        result = {
            "num_holdings": len(tickers),
            "tickers": tickers,
            "total_long_exposure": round(total_long, 4),
            "total_short_exposure": round(total_short, 4),
            "net_exposure": round(total_long - total_short, 4),
            "gross_exposure": round(total_long + total_short, 4),
            "lookback_days": validated_lookback,
            # Add more analysis results here
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Error in portfolio analysis: {str(e)}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

PORTFOLIO_TOOL_NAME_DESCRIPTION = (
    "Analyze [aspect] of a portfolio. Returns [metrics description]. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: portfolio_tool_name(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, "
    "'TSLA': {'allocation': 0.5, 'position': 'short'}}, lookback_days=126)"
)

PORTFOLIO_TOOL_NAME_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "lookback_days": {
            "type": "integer",
            "description": "Historical lookback period in trading days",
            "minimum": 30,
            "maximum": 756,
            "default": 252
        }
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

PORTFOLIO_TOOL_NAME_TOOL = {
    "name": "portfolio_tool_name",
    "description": PORTFOLIO_TOOL_NAME_DESCRIPTION,
    "parameters": PORTFOLIO_TOOL_NAME_PARAMETERS,
    "function": portfolio_tool_name,
}


# ==============================================================================
# STANDALONE TESTING
# ==============================================================================

if __name__ == "__main__":
    # Sample portfolio for testing
    test_portfolio = {
        "AAPL": {"allocation": 0.25, "position": "long"},
        "MSFT": {"allocation": 0.25, "position": "long"},
        "GOOGL": {"allocation": 0.20, "position": "long"},
        "TSLA": {"allocation": 0.15, "position": "short"},
        "META": {"allocation": 0.15, "position": "short"},
    }

    print("Test 1: Basic portfolio analysis")
    print(portfolio_tool_name(portfolio_dict=test_portfolio))
    print()

    print("Test 2: With custom lookback")
    print(portfolio_tool_name(portfolio_dict=test_portfolio, lookback_days=126))
    print()

    print("Test 3: Missing portfolio (validation error)")
    print(portfolio_tool_name(portfolio_dict=None))
