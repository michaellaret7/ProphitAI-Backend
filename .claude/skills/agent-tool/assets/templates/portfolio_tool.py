"""
[TOOL_NAME] - Portfolio analysis tool template.

This tool analyzes [aspect] of a portfolio.
"""

from app.core.atlas.tools_v2.decorator import agent_tool, Param
from app.core.atlas.tools_v2.responses import success_response, error_response
from typing import Annotated, Optional


# ================================
# --> Helper funcs
# ================================


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_tool_name")
def portfolio_tool_name(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=10)] = 1,
    *,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Analyze [aspect] of a portfolio.

    Args:
        tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights matching tickers (e.g., [0.40, 0.35, 0.25])
        years_back: Historical lookback period in years

    Returns:
        Dict with portfolio analysis results

    Examples:
        portfolio_tool_name(
            tickers=['AAPL', 'MSFT', 'GOOGL'],
            weights=[0.40, 0.35, 0.25],
            years_back=1
        )
        >>> {"success": True, "data": {"num_holdings": 3, ...}}

    Raises:
        Exception: If portfolio data is invalid or analysis fails
    """
    if len(tickers) != len(weights):
        return error_response("tickers and weights must have the same length")

    try:
        # =====================================================================
        # CORE ANALYSIS LOGIC HERE
        # =====================================================================

        result = {
            "num_holdings": len(tickers),
            "tickers": tickers,
            "weights": weights,
            "total_weight": round(sum(weights), 4),
            "years_back": years_back,
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Error in portfolio analysis: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print("Test 1: Basic portfolio analysis")
    print(portfolio_tool_name(
        tickers=["AAPL", "MSFT", "GOOGL"],
        weights=[0.40, 0.35, 0.25],
    ))
    print()

    print("Test 2: With custom lookback")
    print(portfolio_tool_name(
        tickers=["AAPL", "MSFT"],
        weights=[0.60, 0.40],
        years_back=3,
    ))
