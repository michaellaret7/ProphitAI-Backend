"""
[TOOL_NAME] - Portfolio analysis tool template.

This tool analyzes [aspect] of a portfolio.
"""

from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
from typing import Annotated, Optional


# ================================
# --> Helper funcs
# ================================


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_tool_name")
def portfolio_tool_name(
    portfolio_dict: Annotated[dict, Schema(PORTFOLIO_DICT_SCHEMA)],
    lookback_days: Annotated[int, Param(min_val=30, max_val=756)] = 252,
    *,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Analyze [aspect] of a portfolio.

    Args:
        portfolio_dict: Portfolio with ticker keys mapping to allocation/position values.
            Example: {'AAPL': {'allocation': 0.5, 'position': 'long'}, ...}
        lookback_days: Historical window for analysis in trading days

    Returns:
        Dict with num_holdings, exposure metrics, and lookback_days

    Examples:
        portfolio_tool_name(
            portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'},
                            'TSLA': {'allocation': 0.5, 'position': 'short'}},
            lookback_days=126
        )
        >>> {"success": True, "data": {"num_holdings": 2, "net_exposure": 0.0, ...}}

    Raises:
        Exception: If portfolio data is invalid or analysis fails
    """
    # Reason: ToolValidator still needed for runtime normalization of portfolio_dict
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    validated_portfolio: dict = v.get('portfolio_dict')

    try:
        # =====================================================================
        # CORE ANALYSIS LOGIC HERE
        # =====================================================================

        tickers = list(validated_portfolio.keys())
        allocations = {t: h['allocation'] for t, h in validated_portfolio.items()}
        positions = {t: h['position'] for t, h in validated_portfolio.items()}

        total_long = sum(a for t, a in allocations.items() if positions[t] == 'long')
        total_short = sum(a for t, a in allocations.items() if positions[t] == 'short')

        result = {
            "num_holdings": len(tickers),
            "tickers": tickers,
            "total_long_exposure": round(total_long, 4),
            "total_short_exposure": round(total_short, 4),
            "net_exposure": round(total_long - total_short, 4),
            "gross_exposure": round(total_long + total_short, 4),
            "lookback_days": lookback_days,
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Error in portfolio analysis: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
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
