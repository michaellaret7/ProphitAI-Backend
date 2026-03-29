"""
Search API endpoints.

Provides security search functionality by ticker, name, CUSIP, ISIN, or CIK.
"""

from fastapi import APIRouter, Query

from prophitai_api.controllers.search import (
    search_controller,
    search_by_ticker_controller,
    search_by_name_controller,
    search_by_cusip_controller,
    search_by_isin_controller,
    search_by_cik_controller,
)

router = APIRouter(tags=["Search"])


@router.get("/search")
async def search(
    query: str = Query(
        ...,
        description="Search query - can be a ticker, company name, CUSIP, ISIN, or CIK",
        min_length=1,
        max_length=100,
    ),
):
    """
    Smart search that auto-detects the input type.

    Uses AI to classify the input and routes to the appropriate search endpoint.
    Supports:
    - Ticker symbols (e.g., 'AAPL', 'MSFT')
    - Company names (e.g., 'Apple', 'Microsoft')
    - CUSIP (e.g., '037833100')
    - ISIN (e.g., 'US0378331005')
    - CIK (e.g., '0000320193')

    Example: GET /api/search?query=AAPL
    """
    return await search_controller(query=query)


@router.get("/search/ticker")
async def search_by_ticker(
    query: str = Query(
        ...,
        description="Ticker symbol to search for (e.g., 'AAPL', 'MSFT')",
        min_length=1,
        max_length=10,
    ),
):
    """
    Search for securities by ticker symbol.

    Returns matching securities with symbol, name, currency, and exchange info.

    Example: GET /api/search/ticker?query=AAPL
    """
    return await search_by_ticker_controller(query=query)


@router.get("/search/name")
async def search_by_name(
    query: str = Query(
        ...,
        description="Company name to search for (e.g., 'Apple', 'Microsoft')",
        min_length=1,
        max_length=100,
    ),
):
    """
    Search for securities by company name.

    Returns matching securities with symbol, name, currency, and exchange info.

    Example: GET /api/search/name?query=Apple
    """
    return await search_by_name_controller(query=query)


@router.get("/search/cusip")
async def search_by_cusip(
    cusip: str = Query(
        ...,
        description="CUSIP identifier (e.g., '037833100' for Apple)",
        min_length=6,
        max_length=9,
    ),
):
    """
    Search for securities by CUSIP identifier.

    CUSIP is a 9-character alphanumeric code that identifies U.S. and Canadian securities.

    Example: GET /api/search/cusip?cusip=037833100
    """
    return await search_by_cusip_controller(cusip=cusip)


@router.get("/search/isin")
async def search_by_isin(
    isin: str = Query(
        ...,
        description="ISIN identifier (e.g., 'US0378331005' for Apple)",
        min_length=12,
        max_length=12,
    ),
):
    """
    Search for securities by ISIN (International Securities Identification Number).

    ISIN is a 12-character alphanumeric code that uniquely identifies a security globally.
    Format: 2-letter country code + 9 alphanumeric characters + 1 check digit.

    Example: GET /api/search/isin?isin=US0378331005
    """
    return await search_by_isin_controller(isin=isin)


@router.get("/search/cik")
async def search_by_cik(
    cik: str = Query(
        ...,
        description="CIK identifier (e.g., '320193' or '0000320193' for Apple)",
        min_length=1,
        max_length=10,
    ),
):
    """
    Search for securities by CIK (SEC Central Index Key).

    CIK is a unique identifier assigned by the SEC to companies filing with them.
    Can be provided with or without leading zeros.

    Example: GET /api/search/cik?cik=320193
    """
    return await search_by_cik_controller(cik=cik)
