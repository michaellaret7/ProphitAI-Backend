"""Institutional holders tools.

Provides tools for fetching institutional ownership analytics
including holder positions, changes in shares, and ownership trends.
"""

from typing import Annotated
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA


# ================================
# --> Helper funcs
# ================================

_KEEP_FIELDS = {
    "investorName",
    "putCallShare",
    "sharesNumber",
    "changeInSharesNumber",
    "changeInSharesNumberPercentage",
    "marketValue",
    "changeInMarketValue",
    "ownership",
    "changeInOwnership",
    "isNew",
    "isSoldOut",
    "holdingPeriod",
    "firstAdded",
}


def _trim(record: dict) -> dict:
    """Keep only the fields that matter for agent consumption."""
    return {k: v for k, v in record.items() if k in _KEEP_FIELDS}


def _fetch_all_pages(ticker: str, year: int, quarter: int) -> list[dict]:
    """Fetch all pages of institutional holder data in parallel."""
    fmp = FMP_API_DATA()

    def fetch_page(page: int):
        return fmp.get_institutional_holder_analytics(ticker, year, quarter, page=page, limit=100)

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_page, page): page for page in range(1, 20)}
        for future in as_completed(futures):
            data = future.result()
            if data:
                results.extend(data)

    return results


# ================================
# --> Tools
# ================================

@agent_tool(name="get_institutional_holders")
def get_institutional_holders(
    ticker: str,
    year: Annotated[int, Param(min_val=2015, max_val=2030)],
    quarter: Annotated[int, Param(min_val=1, max_val=4)],
    row_limit: Annotated[int, Param(min_val=1, max_val=1000)] = 50,
) -> str:
    """
    Get institutional ownership analytics for a ticker showing which institutions
    bought or sold shares in a given quarter.

    Fetches holder-level analytics including position sizes, share changes,
    and ownership percentages. Only returns institutions that changed their
    position (bought or sold) during the quarter.

    **Data Returned (per holder):**
    - investorName: Institution name (e.g., 'Vanguard Group', 'BlackRock')
    - sharesNumber: Total shares held at end of quarter
    - changeInSharesNumber: Net shares bought (+) or sold (-) during quarter
    - ownershipPercent: Percentage of outstanding shares owned
    - marketValue: Dollar value of position

    **Use Cases:**
    - Smart money tracking: See what major institutions are buying/selling
    - Ownership concentration: Identify heavily institutionally-owned stocks
    - Momentum signals: Rising institutional buying can precede price moves
    - Risk assessment: Large institutional selling may signal concerns

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'AAL')
        year: Filing year (e.g., 2025)
        quarter: Filing quarter (1-4)
        row_limit: Maximum number of holders to return, sorted by absolute
            change in shares. Default 50.

    Returns:
        List of institutional holders with position data, filtered to only
        those that changed their position during the quarter

    Examples:
        get_institutional_holders(ticker='AAPL', year=2025, quarter=3)
        >>> {"success": True, "data": [{"investorName": "Vanguard Group", "changeInSharesNumber": 500000, ...}]}

        get_institutional_holders(ticker='AAL', year=2025, quarter=3, row_limit=20)
        >>> {"success": True, "data": [...]}

    Raises:
        Exception: If ticker is invalid or data is unavailable for the period
    """
    ticker = ticker.upper()

    try:
        results = _fetch_all_pages(ticker, year, quarter)

        if not results:
            return error_response(f"No institutional holder data found for {ticker} {year}Q{quarter}")

        # Reason: filter out institutions that didn't change their position
        results = [r for r in results if r.get('changeInSharesNumber', 0) != 0]

        # Reason: sort by absolute change to surface the biggest movers first
        results.sort(key=lambda r: abs(r.get('changeInSharesNumber', 0)), reverse=True)
        results = [_trim(r) for r in results[:row_limit]]

        return success_response({
            "ticker": ticker,
            "period": f"{year}Q{quarter}",
            "num_holders": len(results),
            "holders": results,
        })
    except Exception as e:
        return error_response(f"Failed to retrieve institutional holders for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_institutional_holders.tool)
