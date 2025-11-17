from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from datetime import datetime
from typing import Optional
from app.utils.decorators.price_data import with_price_data
from app.utils.decorators.tool_validation import validate_ticker_arg, log_simulation_data_range
from app.utils.simulation_utils import filter_series_by_date
from app.core.calculations.core.config import DEFAULT_LOOKBACK_SHORT

@validate_ticker_arg()
@with_price_data(lookback_days=DEFAULT_LOOKBACK_SHORT, include_dividends=False)
@log_simulation_data_range()
def get_weekly_returns(ticker: str, price_data=None, _simulation_date: Optional[datetime] = None, **kwargs) -> str:
    """Get weekly returns for the last year for a given ticker.

    Args:
        ticker: Stock ticker symbol
        price_data: Optional pre-fetched price data (from decorator)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents.
                         If provided, uses this as cutoff date instead of current time.

    Note: Uses @validate_ticker_arg() decorator to validate BEFORE @with_price_data fetches data.
    """
    try:
        # Filter price data by simulation date if provided
        filtered_data = filter_series_by_date(price_data, _simulation_date)

        # Resample to weekly and calculate returns
        weekly_prices = filtered_data.resample('W').last()
        weekly_returns = weekly_prices.pct_change().dropna()

        # Convert to dictionary with string dates and format as percentages
        return success_response({
            "ticker": ticker,
            "weekly_returns": {str(date.date()): f"{round(ret * 100, 2)}%" for date, ret in weekly_returns.items()},
            "total_weeks": len(weekly_returns),
            "average_weekly_return": f"{round(weekly_returns.mean() * 100, 2)}%" if not weekly_returns.empty else "0%"
        })
    except Exception as e:
        return error_response(f"Failed to get weekly returns for {ticker}: {str(e)}")

# Tool Schema Constants
GET_WEEKLY_RETURNS_DESCRIPTION = (
    "Get weekly returns for the last year (252 trading days) for a given ticker. "
    "Returns dictionary with ticker symbol, weekly returns as percentage strings with dates, total weeks analyzed, and average weekly return. "
    "Data source: Historical price data from market database. "
    "CRITICAL: You MUST provide the ticker parameter as a valid stock symbol. "
    "Example: get_weekly_returns(ticker='AAPL')"
)

GET_WEEKLY_RETURNS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol to analyze (e.g., 'AAPL', 'MSFT', 'TSLA')",
            "pattern": "^[A-Z]{1,5}$"
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_WEEKLY_RETURNS_TOOL = {
    "name": "get_weekly_returns",
    "description": GET_WEEKLY_RETURNS_DESCRIPTION,
    "parameters": GET_WEEKLY_RETURNS_PARAMETERS,
    "function": get_weekly_returns,
}