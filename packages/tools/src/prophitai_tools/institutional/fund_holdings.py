"""Fund 13F Holdings Tool - Look up a hedge fund's portfolio from SEC 13F filings.

Resolves fund names to CIK numbers, then fetches their quarterly holdings
from the institutional ownership extract endpoint.
"""

from typing import Annotated, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.clients.fmp import FMP_API_DATA


# ================================
# --> Helper funcs
# ================================

_KEEP_FIELDS = {"symbol", "nameOfIssuer", "shares", "value", "titleOfClass", "putCallShare"}


def _trim(record: dict) -> dict:
    """Keep only the fields that matter for agent consumption."""
    return {k: v for k, v in record.items() if k in _KEEP_FIELDS}


def _resolve_cik(fund_name: str) -> tuple[str, str]:
    """Search for an institutional filer by name and return (cik, matched_name).

    Tries each search result and returns the first one that has 13F filing
    dates, since name search often returns subsidiaries that don't file 13Fs.

    Raises:
        ValueError: If no matching institutions are found or none have 13F filings.
    """
    fmp = FMP_API_DATA()
    results = fmp.search_institution_by_name(fund_name)

    if not results:
        raise ValueError(f"No institutional filers found matching '{fund_name}'")

    # Reason: first result is often a subsidiary without 13F filings,
    # so check each candidate for actual filing dates
    for candidate in results:
        dates = fmp.get_institutional_ownership_dates(candidate["cik"])
        if dates:
            return candidate["cik"], candidate["name"]

    return results[0]["cik"], results[0]["name"]


def _fetch_all_holding_pages(cik: str, year: int, quarter: int) -> list[dict]:
    """Fetch all pages of 13F holding data in parallel."""
    fmp = FMP_API_DATA()

    def fetch_page(page: int):
        return fmp.get_institutional_ownership_extract(cik, year, quarter, page=page, limit=100)

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_page, page): page for page in range(20)}
        for future in as_completed(futures):
            data = future.result()
            if data:
                results.extend(data)

    return results


# ================================
# --> Tools
# ================================

@agent_tool(name="get_fund_13f_holdings", category="institutional")
def get_fund_13f_holdings(
    fund_name: str,
    year: Annotated[int, Param(min_val=2015, max_val=2030)],
    quarter: Annotated[int, Param(min_val=1, max_val=4)],
    cik: Optional[str] = None,
    row_limit: Annotated[int, Param(min_val=1, max_val=500)] = 50,
) -> str:
    """
    Get a hedge fund or institution's 13F portfolio holdings for a given quarter.

    Looks up the fund by name (via SEC CIK search), then retrieves their full
    13F filing to show every stock position they held at quarter end.

    **Data Returned (per holding):**
    - symbol: Stock ticker (e.g., 'AAPL')
    - nameOfIssuer: Company name (e.g., 'APPLE INC')
    - shares: Number of shares held
    - value: Dollar value of the position
    - titleOfClass: Security class (e.g., 'COM', 'CL A', 'CL B')
    - putCallShare: Whether position is shares, puts, or calls

    **Use Cases:**
    - Smart money tracking: See what top funds are holding
    - Portfolio cloning: Replicate a fund's top positions
    - Sector allocation analysis: Understand a fund's sector bets
    - Position change monitoring: Compare holdings across quarters

    Args:
        fund_name: Name of the fund or institution (e.g., 'Berkshire Hathaway',
            'Bridgewater', 'Citadel'). Used for CIK lookup unless cik is provided.
        year: Filing year (e.g., 2024)
        quarter: Filing quarter (1-4)
        cik: Optional CIK number to skip name search (e.g., '0001067983').
            Use this if you already know the fund's CIK.
        row_limit: Maximum number of holdings to return, sorted by position
            value descending. Default 50.

    Returns:
        List of fund holdings with position data, sorted by value

    Examples:
        get_fund_13f_holdings(fund_name='Berkshire Hathaway', year=2024, quarter=4)
        get_fund_13f_holdings(fund_name='Bridgewater', year=2024, quarter=3, row_limit=20)
        get_fund_13f_holdings(fund_name='Citadel', year=2024, quarter=4, cik='0001423053')
    """
    try:
        if cik:
            matched_name = fund_name
        else:
            cik, matched_name = _resolve_cik(fund_name)

        results = _fetch_all_holding_pages(cik, year, quarter)

        if not results:
            return error_response(
                f"No 13F holdings found for {matched_name} (CIK: {cik}) in {year}Q{quarter}"
            )

        # Reason: parallel page fetches can return overlapping records,
        # deduplicate by (symbol, titleOfClass, putCallShare) composite key
        seen: set[tuple] = set()
        unique: list[dict] = []
        for r in results:
            key = (r.get("symbol"), r.get("titleOfClass"), r.get("putCallShare"))
            if key not in seen:
                seen.add(key)
                unique.append(r)

        # Reason: sort by value descending to surface largest positions first
        unique.sort(key=lambda r: r.get("value", 0), reverse=True)
        trimmed = [_trim(r) for r in unique[:row_limit]]

        return success_response({
            "fund_name": matched_name,
            "cik": cik,
            "period": f"{year}Q{quarter}",
            "num_holdings": len(trimmed),
            "holdings": trimmed,
        })
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(f"Failed to retrieve 13F holdings for {fund_name}: {str(e)}")



