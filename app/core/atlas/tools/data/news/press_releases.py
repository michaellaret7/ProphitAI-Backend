"""Press releases tools."""

from app.core.atlas.tools.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from datetime import datetime, date, timedelta
from typing import Optional
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time
from app.utils.token_count import get_token_count
import pandas as pd

@log_simulation_data_range()
def get_press_releases(
    ticker: str,
    row_limit: int = 1000,
    days_back: int = 30,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get press releases for a given ticker within a date range.

    Args:
        ticker: The ticker to get the press releases for
        days_back: Number of days to look back from today (or simulation date). Default 30 days.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        JSON formatted string with press release data including:
        - Date of press release
        - Title and content
        - Source information
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.require_numeric('row_limit', row_limit, min_val=1, max_val=1000)
    v.require_numeric('days_back', days_back, min_val=1, max_val=365)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    row_limit = v.get('row_limit')
    days_back = v.get('days_back')

    try:
        # Determine "today" - use simulation date if provided, otherwise current UTC time
        to_date = _simulation_date if _simulation_date else get_current_utc_time()

        # Calculate from_date as to_date minus days_back
        from_date = to_date - timedelta(days=days_back)

        # Format dates as YYYY-MM-DD strings
        from_date_str = from_date.strftime('%Y-%m-%d')
        to_date_str = to_date.strftime('%Y-%m-%d')

        # Fetch press releases
        fmp = FMP_API_DATA()
        data = fmp.get_press_releases(
            ticker=ticker,
            limit=1000,
            from_date=from_date_str,
            to_date=to_date_str
        )

        df = pd.DataFrame(data)
        df.drop(columns=['image', 'url'], inplace=True)
        data = df.to_dict(orient='records')[:row_limit]

        return success_response(data)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
GET_PRESS_RELEASES_DESCRIPTION = (
    "Fetch official press releases for a specific stock ticker. "
    "Returns a list of company press releases including title, text content, publication date, and source. "
    "Press releases are official corporate announcements directly from the company. "
    "\n\n**Data Fields:**"
    "\n  - symbol: Stock ticker"
    "\n  - publishedDate: Date the press release was published"
    "\n  - title: Press release headline"
    "\n  - text: Full press release text content"
    "\n  - site: Source/publisher"
    "\n\n**Use Cases:**"
    "\n  - Tracking official company announcements"
    "\n  - Monitoring earnings reports, product launches, M&A activity"
    "\n  - Corporate event tracking"
    "\n  - Due diligence and fundamental research"
    "\n\n**Examples:**"
    "\n  get_press_releases(ticker='AAPL', row_limit=10, days_back=7)"
    "\n  get_press_releases(ticker='TSLA', row_limit=20, days_back=90)"
)

GET_PRESS_RELEASES_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"
        },
        "row_limit": {
            "type": "integer",
            "description": (
                "Maximum number of press releases to return (max 1000). "
                "Default is 1000."
            ),
            "default": 1000
        },
        "days_back": {
            "type": "integer",
            "description": (
                "Number of days to look back from today. "
                "Range: 1-365 days. Default is 30 days."
            ),
            "default": 30
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_PRESS_RELEASES_TOOL = {
    "name": "get_press_releases",
    "description": GET_PRESS_RELEASES_DESCRIPTION,
    "parameters": GET_PRESS_RELEASES_PARAMETERS,
    "function": get_press_releases,
}
