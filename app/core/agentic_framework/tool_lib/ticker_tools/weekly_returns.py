import yaml
from app.utils.decorators.price_data import with_price_data

@with_price_data(lookback_days=252, include_dividends=False)
def get_weekly_returns(ticker: str, price_data=None, **kwargs) -> str:
    """Get weekly returns for the last year for a given ticker."""
    try:
        # Resample to weekly and calculate returns
        weekly_prices = price_data.resample('W').last()
        weekly_returns = weekly_prices.pct_change().dropna()

        # Convert to dictionary with string dates and format as percentages
        return yaml.dump({
            "success": True,
            "data": {
                "ticker": ticker,
                "weekly_returns": {str(date.date()): f"{round(ret * 100, 2)}%" for date, ret in weekly_returns.items()},
                "total_weeks": len(weekly_returns),
                "average_weekly_return": f"{round(weekly_returns.mean() * 100, 2)}%" if not weekly_returns.empty else "0%"
            }
        }, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": f"Failed to get weekly returns for {ticker}: {str(e)}"}, default_flow_style=False)

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