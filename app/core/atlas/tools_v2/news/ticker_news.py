"""Ticker news tools.

Fetches stock news, press releases, and analyst news (price target
and grade updates) for a given ticker via the FMP API.
"""

from datetime import timedelta
from typing import Annotated, Literal, Optional

import pandas as pd

from app.core.atlas.tools_v2.decorator import agent_tool, Param
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

# Reason: columns that waste tokens and provide no analytical value
_DROP_COLUMNS = {"image", "url"}


def _fetch_stock_news(
    fmp: FMP_API_DATA, ticker: str, limit: int,
    from_date: str, to_date: str,
) -> list[dict]:
    """Fetch general stock news articles."""
    data = fmp.get_stock_news(
        ticker=ticker, limit=limit, from_date=from_date, to_date=to_date,
    )
    return _clean(data)


def _fetch_press_releases(
    fmp: FMP_API_DATA, ticker: str, limit: int,
    from_date: str, to_date: str,
) -> list[dict]:
    """Fetch company press releases."""
    data = fmp.get_press_releases(
        ticker=ticker, limit=limit, from_date=from_date, to_date=to_date,
    )
    return _clean(data)


def _fetch_analyst_news(
    fmp: FMP_API_DATA, ticker: str, limit: int,
) -> list[dict]:
    """Fetch combined price-target and grade news."""
    pt_data = fmp.get_price_target_news(ticker=ticker, limit=limit) or []
    grade_data = fmp.get_stock_grade_news(ticker=ticker, limit=limit) or []

    combined = []
    for item in pt_data:
        item["news_type"] = "price_target"
        combined.append(item)
    for item in grade_data:
        item["news_type"] = "grade"
        combined.append(item)

    # Reason: sort by date descending so most recent analyst actions appear first
    combined.sort(key=lambda x: x.get("publishedDate", ""), reverse=True)
    return _clean(combined[:limit])


def _clean(data: list[dict]) -> list[dict]:
    """Drop low-value columns from news records."""
    if not data:
        return []
    df = pd.DataFrame(data)
    cols_to_drop = [c for c in _DROP_COLUMNS if c in df.columns]
    if cols_to_drop:
        df.drop(columns=cols_to_drop, inplace=True)
    return df.to_dict(orient="records")


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ticker_news")
def get_ticker_news(
    ticker: str,
    news_type: Literal["stock_news", "press_releases", "analyst_news"] = "stock_news",
    limit: Annotated[int, Param(min_val=1, max_val=500)] = 25,
    days_back: Annotated[int, Param(min_val=1, max_val=1095)] = 30,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Fetch news for a specific stock ticker from the FMP API.

    Supports three news categories that cover different aspects of
    company and analyst activity.

    **News Types:**
    - stock_news: General news articles mentioning the ticker (earnings,
      product launches, M&A, market commentary)
    - press_releases: Official company press releases filed with exchanges
    - analyst_news: Combined price-target changes and rating upgrades/downgrades
      from Wall Street analysts (not date-filtered — returns most recent entries)

    **Returned Fields (vary by type):**
    - symbol, publishedDate, title, text, site (stock_news / press_releases)
    - symbol, publishedDate, analystName, priceTarget, newsTitle, news_type (analyst_news)

    **Use Cases:**
    - Company-specific news monitoring and sentiment analysis
    - Tracking analyst rating and price-target changes
    - Event-driven research (earnings, product launches, regulatory actions)
    - Due diligence and fundamental research

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'NVDA')
        news_type: Category of news to fetch
        limit: Maximum number of articles to return
        days_back: Lookback window in calendar days (stock_news and press_releases only)

    Returns:
        List of news records with title, date, content, and source fields

    Examples:
        get_ticker_news(ticker='AAPL', news_type='stock_news', limit=10, days_back=7)
        >>> {"success": True, "data": [{"title": "...", "publishedDate": "...", ...}]}

        get_ticker_news(ticker='NVDA', news_type='analyst_news', limit=20)
        >>> {"success": True, "data": [{"newsTitle": "...", "priceTarget": 150, ...}]}

    Raises:
        ValueError: If ticker is invalid or no data found
    """
    ticker = ticker.strip().upper()

    if not ticker:
        return error_response("ticker is required and cannot be empty")

    try:
        fmp = FMP_API_DATA()

        if _simulation_date:
            to_date = _simulation_date
            from_dt = pd.Timestamp(to_date) - timedelta(days=days_back)
            from_date = str(from_dt.strftime("%Y-%m-%d"))
        else:
            now = get_current_utc_time()
            to_date = now.strftime("%Y-%m-%d")
            from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

        if news_type == "stock_news":
            records = _fetch_stock_news(fmp, ticker, limit, from_date, to_date)
        elif news_type == "press_releases":
            records = _fetch_press_releases(fmp, ticker, limit, from_date, to_date)
        else:
            records = _fetch_analyst_news(fmp, ticker, limit)

        if not records:
            return error_response(
                f"No {news_type} found for {ticker} in the last {days_back} days"
            )

        return success_response(records)
    except Exception as e:
        return error_response(f"Failed to fetch {news_type} for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print("=== Schema ===")
    print(get_ticker_news.tool)
    print()
    print("=== Stock News (AAPL, 5 articles, 7 days) ===")
    print(get_ticker_news(ticker="AAPL", news_type="stock_news", limit=5, days_back=7))
    print()
    print("=== Press Releases (AAPL, 5 articles) ===")
    print(get_ticker_news(ticker="AAPL", news_type="press_releases", limit=5))
    print()
    print("=== Analyst News (AAPL, 5 articles) ===")
    print(get_ticker_news(ticker="AAPL", news_type="analyst_news", limit=5))
