from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
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
def get_ticker_news(
    ticker: str,
    row_limit: int = 1000,
    days_back: int = 30,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get news for a given ticker within a date range.
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
        # Fetch news
        if _simulation_date:
            to_date = _simulation_date
            from_date = to_date - timedelta(days=days_back)
        else:
            to_date = get_current_utc_time()
            from_date = to_date - timedelta(days=days_back)

        fmp = FMP_API_DATA()
        data = fmp.get_stock_news(ticker=ticker, limit=1000, from_date=from_date, to_date=to_date)

        df = pd.DataFrame(data)
        df.drop(columns=['image', 'url'], inplace=True)

        data = df.to_dict(orient='records')[:row_limit]

        return success_response(data)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
GET_TICKER_NEWS_DESCRIPTION = (
    "Fetch news articles for a specific stock ticker. "
    "Returns a list of news articles including title, text content, publication date, site, and symbol. "
    "\n\n**Data Fields:**"
    "\n  - symbol: Stock ticker"
    "\n  - publishedDate: Date the article was published"
    "\n  - title: Article headline"
    "\n  - text: Full article text content"
    "\n  - site: News source/publisher"
    "\n\n**Use Cases:**"
    "\n  - Company-specific news monitoring"
    "\n  - Sentiment analysis for individual stocks"
    "\n  - Event tracking (earnings, product launches, etc.)"
    "\n  - Due diligence research"
    "\n\n**Examples:**"
    "\n  get_ticker_news(ticker='AAPL', row_limit=10, days_back=7)"
    "\n  get_ticker_news(ticker='MSFT', row_limit=50, days_back=30)"
)

GET_TICKER_NEWS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"
        },
        "row_limit": {
            "type": "integer",
            "description": (
                "Maximum number of articles to return (max 1000). "
                "Default is 1000."
            ),
            "default": 1000
        },
        "days_back": {
            "type": "integer",
            "description": (
                "Number of days to look back from today. "
                "Range: 1-1095 days. Default is 30 days."
            ),
            "default": 30
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_TICKER_NEWS_TOOL = {
    "name": "get_ticker_news",
    "description": GET_TICKER_NEWS_DESCRIPTION,
    "parameters": GET_TICKER_NEWS_PARAMETERS,
    "function": get_ticker_news,
}

