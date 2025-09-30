import yaml
from app.repositories.fundamental_data import get_fundamental_data as _get_fundamental_data

def get_fundamental_data(ticker: str, statement_type: str, quarters_back: int = 2) -> str:
    """Wrapper function to return YAML format."""

    if not isinstance(ticker, str) or not ticker:
        return yaml.dump({"success": False, "error": "Parameter 'ticker' must be a non-empty string."}, default_flow_style=False)
    if not isinstance(statement_type, str) or statement_type not in ["income_statement", "balance_sheet", "cash_flow", "financial_ratios"]:
        return yaml.dump({"success": False, "error": f"Parameter 'statement_type' must be one of: {', '.join(['income_statement', 'balance_sheet', 'cash_flow', 'financial_ratios'])}."}, default_flow_style=False)
    if not isinstance(quarters_back, int) or quarters_back < 1:
        return yaml.dump({"success": False, "error": "Parameter 'quarters_back' must be a positive integer."}, default_flow_style=False)

    try:
        data = _get_fundamental_data(ticker, statement_type, quarters_back)
        result = {"success": True, "data": data}
    except Exception as e:
        result = {"success": False, "error": f"Failed to retrieve fundamental data: {str(e)}"}

    return yaml.dump(result, default_flow_style=False)

# Tool Schema Constants
GET_TICKER_FUNDAMENTAL_DATA_DESCRIPTION = (
    "Get fundamental financial data for a ticker including income statements, balance sheets, cash flow statements, financial ratios, or analyst estimates.\n\n"
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
            "description": "Type of fundamental data to retrieve. Must be one of: 'income_statement', 'balance_sheet', 'cash_flow', 'financial_ratios', 'analyst_estimates'.",
            "enum": ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"]
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