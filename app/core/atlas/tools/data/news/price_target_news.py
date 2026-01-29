"""Price target news tools."""

from app.core.atlas.tools.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from datetime import datetime
from typing import Optional
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.token_count import get_token_count
import pandas as pd
from app.utils.time_utils import get_current_utc_time
from datetime import timedelta

@log_simulation_data_range()
def get_price_target_news(
    ticker: str,
    row_limit: int = 1000,
    days_back: int = 30,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get price target news for a given ticker within a date range.
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.require_numeric('row_limit', row_limit, min_val=1, max_val=1000)
    v.require_numeric('days_back', days_back, min_val=1, max_val=1095)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    row_limit = v.get('row_limit')
    days_back = v.get('days_back')

    try:
        # Fetch price target news
        if _simulation_date:
            to_date = _simulation_date
            from_date = to_date - timedelta(days=days_back)
        else:
            to_date = get_current_utc_time()
            from_date = to_date - timedelta(days=days_back)

        fmp = FMP_API_DATA()

        # for i in range(0, 3):
        data1 = fmp.get_price_target_news(ticker=ticker, page=0, limit=1000)
        data2 = fmp.get_price_target_news(ticker=ticker, page=1, limit=1000)
        data3 = fmp.get_price_target_news(ticker=ticker, page=2, limit=1000)
        data = data1 + data2 + data3

        if data is None or len(data) == 0:
            return error_response(f'No data found, for {ticker}, please try a different ticker.')

        df = pd.DataFrame(data)

        # Convert publishedDate string to datetime for filtering and sorting
        df['publishedDate'] = pd.to_datetime(df['publishedDate']).dt.tz_convert('UTC').dt.tz_localize(None)

        # Filter by date range (from_date to to_date)
        df = df[(df['publishedDate'] >= from_date) & (df['publishedDate'] <= to_date)]

        # Sort by date descending (most recent first)
        df.sort_values('publishedDate', ascending=False, inplace=True)

        # Convert datetime back to string format for output
        df['publishedDate'] = df['publishedDate'].dt.strftime('%Y-%m-%d')

        df.drop(columns=['newsURL', 'newsBaseURL'], inplace=True)
        data = df.to_dict(orient='records')[:row_limit]

        return success_response(data)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
GET_PRICE_TARGET_NEWS_DESCRIPTION = (
    "Fetch analyst price target announcements for a specific stock ticker. "
    "Returns a list of price target updates from analysts including the target price, analyst firm, "
    "publication date, and article details. Note: Price target news is published less frequently than "
    "regular news (typically quarterly or after major events). "
    "\n\n**Data Fields:**"
    "\n  - symbol: Stock ticker"
    "\n  - publishedDate: Date the price target was published"
    "\n  - newsTitle: Headline of the price target announcement"
    "\n  - priceTarget: Analyst's target price"
    "\n  - adjPriceTarget: Adjusted target price"
    "\n  - priceWhenPosted: Stock price when target was set"
    "\n  - analystName: Name of the analyst"
    "\n  - analystCompany: Firm/company of the analyst"
    "\n  - newsPublisher: Publisher of the news"
    "\n\n**Use Cases:**"
    "\n  - Tracking analyst sentiment and price expectations"
    "\n  - Monitoring target price changes over time"
    "\n  - Identifying consensus targets and outliers"
    "\n  - Researching analyst upgrades/downgrades"
    "\n\n**Important Notes:**"
    "\n  - Price targets are published infrequently (not daily)"
    "\n  - Recommend using days_back=180-365 for meaningful results"
    "\n  - Default days_back=30 may return few or no results"
    "\n\n**Examples:**"
    "\n  get_price_target_news(ticker='AAPL', row_limit=10, days_back=180)"
    "\n  get_price_target_news(ticker='TSLA', row_limit=20, days_back=365)"
)

GET_PRICE_TARGET_NEWS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"
        },
        "row_limit": {
            "type": "integer",
            "description": (
                "Maximum number of price target announcements to return (max 1000). "
                "Default is 1000."
            ),
            "default": 1000
        },
        "days_back": {
            "type": "integer",
            "description": (
                "Number of days to look back from today. "
                "Range: 1-1095 days. Default is 30 days. "
                "Recommend 180-365 days for sufficient results since price targets are published infrequently."
            ),
            "default": 30
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_PRICE_TARGET_NEWS_TOOL = {
    "name": "get_price_target_news",
    "description": GET_PRICE_TARGET_NEWS_DESCRIPTION,
    "parameters": GET_PRICE_TARGET_NEWS_PARAMETERS,
    "function": get_price_target_news,
}
