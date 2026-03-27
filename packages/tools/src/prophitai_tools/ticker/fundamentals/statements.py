"""Financial statement tools.

Provides tools for fetching fundamental financial data including
income statements, balance sheets, cash flow statements, and financial ratios.
"""

from typing import Annotated, Literal

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.repositories.fundamentals.statements import get_fundamental_data as _get_fundamental_data


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ticker_fundamental_data", category="fundamentals")
def get_ticker_fundamental_data(
    ticker: str,
    statement_type: Literal['income_statement', 'balance_sheet', 'cash_flow', 'financial_ratios'],
    quarters_back: Annotated[int, Param(min_val=1, max_val=20)] = 2,
) -> str:
    """
    Get fundamental financial data for a ticker including income statements,
    balance sheets, cash flow statements, or financial ratios.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'KO')
        statement_type: Type of fundamental data to retrieve
        quarters_back: Number of quarters of historical data to retrieve

    Returns:
        YAML-formatted financial statement data for the requested periods

    Examples:
        get_ticker_fundamental_data(ticker='KO', statement_type='balance_sheet', quarters_back=2)
        >>> {"success": True, "data": [...]}

        get_ticker_fundamental_data(ticker='AAPL', statement_type='income_statement')
        >>> {"success": True, "data": [...]}

    Raises:
        Exception: If ticker is invalid or data retrieval fails
    """
    try:
        data = _get_fundamental_data(ticker.upper(), statement_type, quarters_back)
        return success_response(data)
    except Exception as e:
        return error_response(f"Failed to retrieve fundamental data for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_ticker_fundamental_data.tool)
