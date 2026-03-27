"""General News Tool - Fetch general financial news from tier-1 publishers.

Uses the FMP API's general news endpoint with sliding window fetching
to collect articles, then filters for tier-1 publishers (WSJ, Bloomberg,
Reuters, NYTimes, Barrons, Financial Times).
"""

from datetime import datetime, timedelta
from typing import Annotated

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_shared.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

TIER_1_PUBLISHERS = [
    "WSJ", "Wall Street Journal", "Bloomberg", "Reuters",
    "NYTimes", "New York Times", "Barrons", "Financial Times",
]


def _generate_date_windows(
    from_date: str, to_date: str, window_days: int = 3,
) -> list[tuple[str, str]]:
    """Generate sliding date windows for chunked API fetching.

    Args:
        from_date: Start date in YYYY-MM-DD format.
        to_date: End date in YYYY-MM-DD format.
        window_days: Size of each window in days.

    Returns:
        List of (window_start, window_end) date string tuples.
    """
    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")

    windows: list[tuple[str, str]] = []
    current_start = start

    while current_start < end:
        current_end = min(current_start + timedelta(days=window_days), end)
        windows.append((
            current_start.strftime("%Y-%m-%d"),
            current_end.strftime("%Y-%m-%d"),
        ))
        current_start = current_end

    return windows


def _fetch_news_with_sliding_window(
    from_date: str, to_date: str, limit_per_window: int = 75,
) -> list[dict]:
    """Fetch news across date range using sliding windows to avoid API limits.

    Args:
        from_date: Start date in YYYY-MM-DD format.
        to_date: End date in YYYY-MM-DD format.
        limit_per_window: Max results per API call.

    Returns:
        Deduplicated list of all news articles from all windows.
    """
    fmp = FMP_API_DATA()
    windows = _generate_date_windows(from_date, to_date, window_days=3)

    all_data: list[dict] = []
    seen: set[tuple] = set()

    for window_start, window_end in windows:
        window_data = fmp.get_general_news(
            limit=limit_per_window,
            from_date=window_start,
            to_date=window_end,
        )

        if not window_data or not isinstance(window_data, list):
            continue

        # Reason: deduplicate articles based on title + publishedDate
        for article in window_data:
            if not isinstance(article, dict):
                continue
            key = (article.get("title"), article.get("publishedDate"))
            if key not in seen:
                seen.add(key)
                all_data.append(article)

    return all_data


def _format_articles(
    articles: list[dict], limit: int, max_text_length: int,
) -> list[dict]:
    """Filter for tier-1 publishers, truncate text, sort, and limit results.

    Args:
        articles: Raw article dicts from the FMP API.
        limit: Maximum number of articles to return.
        max_text_length: Truncate article text to this many characters.

    Returns:
        Filtered, sorted, and truncated article list.
    """
    # Reason: only keep articles from high-quality publishers
    filtered = [
        a for a in articles
        if a.get("publisher") in TIER_1_PUBLISHERS
    ]

    # Reason: most recent articles first
    filtered.sort(key=lambda x: x.get("publishedDate", ""), reverse=True)
    filtered = filtered[:limit]

    formatted: list[dict] = []
    for article in filtered:
        text = article.get("text", "") or ""
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        # Reason: strip time component from publishedDate for cleaner output
        pub_date = article.get("publishedDate", "")
        if pub_date and " " in pub_date:
            pub_date = pub_date.split(" ")[0]

        formatted.append({
            "title": article.get("title", ""),
            "text": text,
            "publishedDate": pub_date,
            "publisher": article.get("publisher", ""),
        })

    return formatted


# ================================
# --> Tools
# ================================

@agent_tool(name="general_news", category="market")
def general_news(
    days_back: Annotated[int, Param(min_val=1, max_val=90)] = 7,
    limit: Annotated[int, Param(min_val=1, max_val=50)] = 10,
    max_text_length: Annotated[int, Param(min_val=100, max_val=5000)] = 500,
) -> str:
    """
    Fetch general financial news from tier-1 publishers via the FMP API.

    Returns articles from major financial publishers only: Wall Street Journal,
    Bloomberg, Reuters, NY Times, Barrons, and Financial Times. Articles are
    deduplicated, sorted by date (newest first), and text is truncated for
    token efficiency.

    **Use Cases:**
    - Market sentiment analysis and macro outlook
    - Tracking major financial events and breaking news
    - Researching market-moving headlines over a time period

    **Publishers Covered:**
    - Wall Street Journal, Bloomberg, Reuters
    - NY Times, Barrons, Financial Times

    Args:
        days_back: Number of days to look back from today (default: 7, max: 90)
        limit: Maximum number of articles to return (default: 10, max: 50)
        max_text_length: Truncate article text to this many characters (default: 500)

    Returns:
        List of articles with title, text, publishedDate, and publisher fields

    Examples:
        general_news(days_back=7, limit=10)
        >>> {"success": True, "data": [{"title": "...", "text": "...", ...}]}

        general_news(days_back=30, limit=25, max_text_length=1000)
        >>> {"success": True, "data": [{"title": "...", "text": "...", ...}]}

    Raises:
        ValueError: If parameter constraints are violated
    """
    try:
        to_dt = get_current_utc_time()

        from_dt = to_dt - timedelta(days=days_back)
        from_date = from_dt.strftime("%Y-%m-%d")
        to_date = to_dt.strftime("%Y-%m-%d")

        raw_articles = _fetch_news_with_sliding_window(from_date, to_date)

        if not raw_articles:
            return error_response(
                f"No general news found in the last {days_back} days. "
                "Try increasing days_back."
            )

        results = _format_articles(raw_articles, limit, max_text_length)

        if not results:
            return error_response(
                f"No tier-1 publisher articles found in the last {days_back} days. "
                "Try increasing days_back to widen the search window."
            )

        return success_response(results)

    except Exception as e:
        return error_response(f"Error fetching general news: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print("=== Schema ===")
    print(general_news.tool)
    print()
    print("=== General News (7 days, 5 articles) ===")
    print(general_news(days_back=7, limit=5))
