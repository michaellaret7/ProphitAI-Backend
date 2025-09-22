from app.repositories.fundamental_data import get_fundamental_data

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