"""Press releases tool — fetches official company press releases via FMP API."""

from datetime import timedelta
from typing import Annotated

import pandas as pd

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

# Reason: columns that waste tokens and provide no analytical value
_DROP_COLUMNS = ["image", "url"]


# ================================
# --> Tools
# ================================

@agent_tool(name="get_press_releases")
def get_press_releases(
    ticker: str,
    days_back: Annotated[int, Param(min_val=1, max_val=365)] = 30,
    row_limit: Annotated[int, Param(min_val=1, max_val=100)] = 25,
) -> str:
    """
    Fetch official press releases for a specific stock ticker from the FMP API.

    Press releases are corporate announcements filed directly by the company
    with exchanges. They include earnings reports, product launches, M&A
    activity, executive changes, and regulatory filings.

    **Returned Fields:**
    - symbol: Stock ticker
    - publishedDate: Date the press release was published
    - title: Press release headline
    - text: Full press release text content
    - site: Source/publisher

    **Use Cases:**
    - Tracking official company announcements
    - Monitoring earnings reports, product launches, M&A activity
    - Corporate event tracking and due diligence
    - Fundamental research and sentiment analysis

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'NVDA')
        days_back: Lookback window in calendar days from today
        row_limit: Maximum number of press releases to return

    Returns:
        List of press release records with title, date, content, and source fields

    Examples:
        get_press_releases(ticker='AAPL', days_back=7, row_limit=10)
        get_press_releases(ticker='TSLA', days_back=90, row_limit=50)
    """
    ticker = str(ticker).strip().upper()
    if not ticker:
        return error_response("ticker is required and cannot be empty")

    try:
        to_date = get_current_utc_time()

        from_date = to_date - timedelta(days=days_back)

        from_date_str = from_date.strftime("%Y-%m-%d")
        to_date_str = to_date.strftime("%Y-%m-%d")

        fmp = FMP_API_DATA()
        data = fmp.get_press_releases(
            ticker=ticker,
            limit=1000,
            from_date=from_date_str,
            to_date=to_date_str,
        )

        if not data:
            return error_response(
                f"No press releases found for {ticker} in the last {days_back} days"
            )

        df = pd.DataFrame(data)
        cols_to_drop = [c for c in _DROP_COLUMNS if c in df.columns]
        if cols_to_drop:
            df.drop(columns=cols_to_drop, inplace=True)

        records = df.to_dict(orient="records")[:row_limit]
        return success_response(records)

    except Exception as e:
        return error_response(f"Failed to fetch press releases for {ticker}: {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print("=== Schema ===")
    print(get_press_releases.tool)
    print()
    print("=== Press Releases (AAPL, 5 articles, 7 days) ===")
    print(get_press_releases(ticker="AAPL", days_back=7, row_limit=5))
