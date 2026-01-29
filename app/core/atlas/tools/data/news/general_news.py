"""General news tools."""

from app.db.core.pull_fmp_data import FMP_API_DATA
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.utils.time_utils import get_current_utc_time
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import tiktoken
import pandas as pd

def _count_tokens(text: str) -> int:
    """Count the number of tokens in a string using tiktoken."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))

class GeneralNews(BaseModel):
    title: str
    text: str
    publishedDate: str
    publisher: str

def _generate_date_windows(from_date: str, to_date: str, window_days: int = 3) -> List[tuple]:
    """
    Generate date windows for sliding window data fetching.

    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
        window_days: Size of each window in days (default: 3)

    Returns:
        List of tuples containing (window_start_date, window_end_date) as strings
    """
    start = datetime.strptime(from_date, '%Y-%m-%d')
    end = datetime.strptime(to_date, '%Y-%m-%d')

    windows = []
    current_start = start

    while current_start < end:
        current_end = min(current_start + timedelta(days=window_days), end)
        windows.append((
            current_start.strftime('%Y-%m-%d'),
            current_end.strftime('%Y-%m-%d')
        ))
        current_start = current_end

    return windows

def _fetch_news_with_sliding_window(limit_per_window: int = 75, from_date: str = None, to_date: str = None) -> List[Dict]:
    """
    Fetch news data using a sliding window approach to get complete dataset.

    Args:
        limit_per_window: Max results per API call (default: 1000)
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format

    Returns:
        Aggregated list of all news articles from all windows, or None if API fails
    """
    fmp_api = FMP_API_DATA()

    # Reason: If no date range specified, make single API call
    if not from_date or not to_date:
        result = fmp_api.get_general_news(limit=limit_per_window, from_date=from_date, to_date=to_date)
        return result if result is not None else []

    # Reason: Generate 3-day windows for the entire date range
    windows = _generate_date_windows(from_date, to_date, window_days=3)

    all_data = []
    seen_articles = set()  # Reason: Track unique articles to avoid duplicates at window boundaries

    for window_start, window_end in windows:
        window_data = fmp_api.get_general_news(
            limit=limit_per_window,
            from_date=window_start,
            to_date=window_end
        )

        if window_data and isinstance(window_data, list):
            # Reason: Deduplicate articles based on title and publishedDate
            for article in window_data:
                if isinstance(article, dict):
                    article_key = (article.get('title'), article.get('publishedDate'))
                    if article_key not in seen_articles:
                        seen_articles.add(article_key)
                        all_data.append(article)

    return all_data

@log_simulation_data_range()
def get_general_news(
    row_limit: int = 500,
    days_back: int = 30,
    _simulation_date: Optional[datetime] = None
):
    """
    Get general news using sliding window approach for large date ranges.

    Args:
        row_limit: Maximum number of results to return (max 1000)
        days_back: Number of days to look back from today (or simulation date). Default 30 days.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        Success response with list of news articles or error response
    """

    TIER_1_PUBLISHERS = [
        'WSJ', 'Wall Street Journal', 'Bloomberg', 'Reuters',
        'NYTimes', 'New York Times', 'Barrons', 'Financial Times'
    ]

    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_numeric('row_limit', row_limit, min_val=1, max_val=1000)
    v.require_numeric('days_back', days_back, min_val=1, max_val=1095)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
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

        data = _fetch_news_with_sliding_window(limit_per_window=1000, from_date=from_date_str, to_date=to_date_str)

        if not isinstance(data, list):
            return error_response(f"Failed to retrieve general news from FMP API. Moving on to next tool.")

        # Reason: Filter for tier 1 publishers only, then validate and convert to Pydantic models
        filtered_data = [
            GeneralNews(**item).model_dump()
            for item in data
            if item.get('publisher') in TIER_1_PUBLISHERS
        ]

        filtered_data = sorted(filtered_data, key=lambda x: x['publishedDate'], reverse=True)[:row_limit]

        df = pd.DataFrame(filtered_data)
        # Handle case where filtered_data is empty to avoid KeyError
        if not df.empty:
            df['publishedDate'] = pd.to_datetime(df['publishedDate']).dt.date

            # Update filtered_data with the cleaned dates
            for i, item in enumerate(filtered_data):
                item['publishedDate'] = str(df.iloc[i]['publishedDate'])

        results = df.to_dict(orient='records')

        return success_response(results)

    except Exception as e:
        return error_response(f"Error retrieving general news: {str(e)}")


# Tool Schema Constants
GET_GENERAL_NEWS_DESCRIPTION = (
    "Fetch general financial news articles from major tier-1 publishers. "
    "Returns a list of articles including title, text snippet, publication date, and publisher. "
    "\n\n**Publishers Covered:**"
    "\n  - Wall Street Journal, Bloomberg, Reuters"
    "\n  - NY Times, Barrons, Financial Times"
    "\n\n**Features:**"
    "\n  - Filters for high-quality sources only"
    "\n  - Supports date ranges with automatic sliding window fetching"
    "\n  - Deduplicates articles"
    "\n\n**Use Cases:**"
    "\n  - Market sentiment analysis"
    "\n  - Tracking major financial events"
    "\n  - Researching specific time periods"
    "\n\n**Examples:**"
    "\n  get_general_news(row_limit=10, days_back=7)"
    "\n  get_general_news(row_limit=50, days_back=30)"
)

GET_GENERAL_NEWS_PARAMETERS = {
    "type": "object",
    "properties": {
        "row_limit": {
            "type": "integer",
            "description": (
                "Maximum number of articles to return (max 1000). "
                "Default is 500."
            ),
            "default": 500
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
    "additionalProperties": False
}

GET_GENERAL_NEWS_TOOL = {
    "name": "get_general_news",
    "description": GET_GENERAL_NEWS_DESCRIPTION,
    "parameters": GET_GENERAL_NEWS_PARAMETERS,
    "function": get_general_news,
}
