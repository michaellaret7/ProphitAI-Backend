"""Financial statement tools.

This module provides tools for fetching fundamental financial data including
income statements, balance sheets, cash flow statements, and financial ratios.
"""

from typing import Optional
from datetime import datetime
from app.repositories.fundamentals.statements import get_fundamental_data as _get_fundamental_data
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.token_count import get_token_count

@log_simulation_data_range()
def get_fundamental_data(ticker: str, statement_type: str, quarters_back: int = 2, _simulation_date: Optional[datetime] = None) -> str:
    """Get fundamental financial data for a ticker.

    Args:
        ticker: Stock ticker symbol
        statement_type: Type of fundamental statement
        quarters_back: Number of quarters to look back. Default is 2.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        YAML formatted string with financial statement data
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.require_enum('statement_type', statement_type, ["income_statement", "balance_sheet", "cash_flow", "financial_ratios"])
    v.require_numeric('quarters_back', quarters_back, min_val=1, max_val=20)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    statement_type = v.get('statement_type')
    quarters_back = v.get('quarters_back')

    try:
        data = _get_fundamental_data(ticker, statement_type, quarters_back, _simulation_date=_simulation_date)
        return success_response(data)
    except Exception as e:
        return error_response(f"Failed to retrieve fundamental data: {str(e)}")

# Tool Schema Constants
GET_TICKER_FUNDAMENTAL_DATA_DESCRIPTION = (
    "Get fundamental financial data for a ticker including income statements, balance sheets, cash flow statements, or financial ratios.\n\n"
    "Example: get_ticker_fundamental_data(ticker='KO', statement_type='balance_sheet', quarters_back=2)"
)

GET_TICKER_FUNDAMENTAL_DATA_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ticker symbol to get fundamental data for. For example, 'AAPL', 'MSFT', 'KO', etc.",
        },
        "statement_type": {
            "type": "string",
            "description": "Type of fundamental data to retrieve. Must be one of: 'income_statement', 'balance_sheet', 'cash_flow', 'financial_ratios'.",
            "enum": ["income_statement", "balance_sheet", "cash_flow", "financial_ratios"]
        },
        "quarters_back": {
            "type": "integer",
            "description": "Number of quarters of historical data to retrieve. Default is 2 (most recent 2 quarters).",
            "default": 2,
            "minimum": 1,
            "maximum": 20
        },
    },
    "required": ["ticker", "statement_type"],
}

GET_TICKER_FUNDAMENTAL_DATA_TOOL = {
    "name": "get_ticker_fundamental_data",
    "description": GET_TICKER_FUNDAMENTAL_DATA_DESCRIPTION,
    "parameters": GET_TICKER_FUNDAMENTAL_DATA_PARAMETERS,
    "function": get_fundamental_data,
}
