from typing import Optional
from datetime import datetime
from app.repositories.fundamental_data import get_fundamental_data as _get_fundamental_data
from app.utils.decorators.tool_validation import validate_ticker_arg, validate_enum_arg, validate_numeric_arg
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

@validate_ticker_arg()
@validate_enum_arg("statement_type", ["income_statement", "balance_sheet", "cash_flow", "financial_ratios"])
@validate_numeric_arg("quarters_back", min_value=1)
@log_simulation_data_range()
def get_fundamental_data(ticker: str = None, statement_type: str = None, quarters_back: int = 2, _simulation_date: Optional[datetime] = None) -> str:
    """Wrapper function to return YAML format.

    Args:
        ticker: Stock ticker symbol
        statement_type: Type of fundamental statement
        quarters_back: Number of quarters to look back
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents
    """

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
            "description": "Number of quarters of historical data to retrieve. Default is 1 (most recent quarter only).",
            "default": 2
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