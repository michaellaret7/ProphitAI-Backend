"""Dividend data tools for corporate actions analysis."""

from typing import Optional
from datetime import datetime
from app.repositories.price_data import get_dividends_series
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.decorators.tool_validation import validate_ticker_arg, validate_numeric_arg
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.simulation_utils import get_date_range, filter_series_by_date
from app.utils.token_count import get_token_count


@validate_ticker_arg()
@validate_numeric_arg("years_back", min_value=1, max_value=20)
@log_simulation_data_range()
def get_dividend_history(
    ticker: str,
    years_back: int = 1,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get historical dividend payment series for a ticker.

    Args:
        ticker: Stock ticker symbol
        years_back: Number of years of dividend history to fetch (default: 1, max: 20)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        JSON formatted string with dividend payment history including:
        - ticker: Stock ticker symbol
        - count: Number of dividend payments
        - items: List of dividend payments with date and amount
    """
    try:
        # Calculate date range based on simulation mode or current date
        start_date, end_date = get_date_range(_simulation_date, lookback_days=years_back * 365)

        # Fetch dividend series from repository
        dividend_series = get_dividends_series(ticker, start_date, end_date)

        # Filter by simulation date if applicable
        dividend_series = filter_series_by_date(dividend_series, _simulation_date)

        # Format as list of dictionaries
        items = [
            {
                "date": str(idx.date()),
                "amount": float(val)
            }
            for idx, val in dividend_series.items()
        ]

        data = {
            "ticker": ticker.upper(),
            "count": len(items),
            "items": items
        }

        return success_response(data)
    except Exception as e:
        return error_response(e)

# Tool Schema Constants
GET_DIVIDEND_HISTORY_DESCRIPTION = (
    "Fetch historical dividend payment data for a stock ticker. "
    "Returns a chronological series of dividend payments including payment dates and amounts. "
    "\n\n**Use Cases:**"
    "\n  - Analyze dividend payment consistency and growth"
    "\n  - Calculate dividend yield trends over time"
    "\n  - Identify dividend cuts or suspensions"
    "\n  - Assess dividend sustainability"
    "\n  - Compare dividend policies across companies"
    "\n\n**Data Returned:**"
    "\n  - ticker: Stock ticker symbol"
    "\n  - count: Total number of dividend payments in period"
    "\n  - items: List of payments with:"
    "\n    - date: Payment date (YYYY-MM-DD)"
    "\n    - amount: Dividend amount per share ($)"
    "\n\n**Examples:**"
    "\n  get_dividend_history(ticker='AAPL', years_back=1)"
    "\n  get_dividend_history(ticker='KO', years_back=5)"
    "\n  get_dividend_history(ticker='JNJ', years_back=10)"
)

GET_DIVIDEND_HISTORY_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'KO', 'JNJ')",
        },
        "years_back": {
            "type": "integer",
            "description": (
                "Number of years of dividend history to retrieve. "
                "Default is 1 year. Maximum is 20 years."
            ),
            "default": 1,
            "minimum": 1,
            "maximum": 20
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_DIVIDEND_HISTORY_TOOL = {
    "name": "get_dividend_history",
    "description": GET_DIVIDEND_HISTORY_DESCRIPTION,
    "parameters": GET_DIVIDEND_HISTORY_PARAMETERS,
    "function": get_dividend_history,
}