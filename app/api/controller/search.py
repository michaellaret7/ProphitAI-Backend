"""
Search controller.

Handles searching for securities by ticker, name, CUSIP, ISIN, or CIK.
Includes smart search that auto-detects the input type.
"""

import asyncio
from typing import Any, Dict

from app.api.response_envelope import ok_envelope
from app.services.search.classify import SearchService
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def search_controller(
    *,
    query: str,
) -> Dict[str, Any]:
    """
    Smart search that auto-detects input type and searches accordingly.

    Uses GPT to classify the input as Name, Ticker, CUSIP, ISIN, or CIK,
    then routes to the appropriate FMP search endpoint.

    Args:
        query: Search query (ticker, company name, CUSIP, ISIN, or CIK)

    Returns:
        Response envelope with search results payload
    """
    search_service = SearchService()
    data = await asyncio.to_thread(search_service.search, query)

    return ok_envelope(
        message=f"Search results for '{query}' retrieved successfully",
        kind="search#smart",
        resource_id=query,
        self_link=f"/api/search?query={query}",
        counts={"totalItems": len(data) if data else 0, "currentItemCount": len(data) if data else 0},
        payload=data,
    )


@handle_controller_errors
async def search_by_ticker_controller(
    *,
    query: str,
) -> Dict[str, Any]:
    """
    Search for securities by ticker symbol.

    Args:
        query: Ticker symbol to search for (e.g., 'AAPL', 'MSFT')

    Returns:
        Response envelope with matching securities
    """
    search_service = SearchService()
    data = await asyncio.to_thread(search_service.get_ticker_search_results, query)

    return ok_envelope(
        message=f"Ticker search results for '{query}' retrieved successfully",
        kind="search#ticker",
        resource_id=query,
        self_link=f"/api/search/ticker?query={query}",
        counts={"totalItems": len(data) if data else 0, "currentItemCount": len(data) if data else 0},
        payload=data,
    )


@handle_controller_errors
async def search_by_name_controller(
    *,
    query: str,
) -> Dict[str, Any]:
    """
    Search for securities by company name.

    Args:
        query: Company name to search for (e.g., 'Apple', 'Microsoft')

    Returns:
        Response envelope with matching securities
    """
    search_service = SearchService()
    data = await asyncio.to_thread(search_service.get_name_search_results, query)

    return ok_envelope(
        message=f"Name search results for '{query}' retrieved successfully",
        kind="search#name",
        resource_id=query,
        self_link=f"/api/search/name?query={query}",
        counts={"totalItems": len(data) if data else 0, "currentItemCount": len(data) if data else 0},
        payload=data,
    )


@handle_controller_errors
async def search_by_cusip_controller(
    *,
    cusip: str,
) -> Dict[str, Any]:
    """
    Search for securities by CUSIP identifier.

    Args:
        cusip: CUSIP number (e.g., '037833100' for Apple)

    Returns:
        Response envelope with matching securities
    """
    search_service = SearchService()
    data = await asyncio.to_thread(search_service.get_cusip_search_results, cusip)

    return ok_envelope(
        message=f"CUSIP search results for '{cusip}' retrieved successfully",
        kind="search#cusip",
        resource_id=cusip,
        self_link=f"/api/search/cusip?cusip={cusip}",
        counts={"totalItems": len(data) if data else 0, "currentItemCount": len(data) if data else 0},
        payload=data,
    )


@handle_controller_errors
async def search_by_isin_controller(
    *,
    isin: str,
) -> Dict[str, Any]:
    """
    Search for securities by ISIN (International Securities Identification Number).

    Args:
        isin: ISIN number (e.g., 'US0378331005' for Apple)

    Returns:
        Response envelope with matching securities
    """
    search_service = SearchService()
    data = await asyncio.to_thread(search_service.get_isin_search_results, isin)

    return ok_envelope(
        message=f"ISIN search results for '{isin}' retrieved successfully",
        kind="search#isin",
        resource_id=isin,
        self_link=f"/api/search/isin?isin={isin}",
        counts={"totalItems": len(data) if data else 0, "currentItemCount": len(data) if data else 0},
        payload=data,
    )


@handle_controller_errors
async def search_by_cik_controller(
    *,
    cik: str,
) -> Dict[str, Any]:
    """
    Search for securities by CIK (SEC Central Index Key).

    Args:
        cik: CIK number (e.g., '320193' for Apple)

    Returns:
        Response envelope with matching securities
    """
    search_service = SearchService()
    data = await asyncio.to_thread(search_service.get_cik_search_results, cik)

    return ok_envelope(
        message=f"CIK search results for '{cik}' retrieved successfully",
        kind="search#cik",
        resource_id=cik,
        self_link=f"/api/search/cik?cik={cik}",
        counts={"totalItems": len(data) if data else 0, "currentItemCount": len(data) if data else 0},
        payload=data,
    )
