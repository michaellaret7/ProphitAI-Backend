"""Controllers for company data endpoints (peers, ESG, revenue segmentation, ownership)."""

import asyncio
from typing import Dict, Any

from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_data.clients.fmp import FMP_API_DATA


@handle_controller_errors
async def get_stock_peers_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle stock peers data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_stock_peers, ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No peer data found for {ticker}",
            kind="fundamentals#stockPeers",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/peers",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Stock peers retrieved successfully",
        kind="fundamentals#stockPeers",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/peers",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_esg_disclosures_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle ESG disclosures data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_esg_disclosures, ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No ESG data found for {ticker}",
            kind="fundamentals#esgDisclosures",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/esg",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="ESG disclosures retrieved successfully",
        kind="fundamentals#esgDisclosures",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/esg",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_revenue_product_segmentation_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle revenue product segmentation data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_revenue_product_segmentation, ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No revenue product segmentation data found for {ticker}",
            kind="fundamentals#revenueProductSegmentation",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/revenue/product-segmentation",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Revenue product segmentation retrieved successfully",
        kind="fundamentals#revenueProductSegmentation",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/revenue/product-segmentation",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_revenue_geographic_segmentation_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle revenue geographic segmentation data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_revenue_geographic_segmentation, ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No revenue geographic segmentation data found for {ticker}",
            kind="fundamentals#revenueGeographicSegmentation",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/revenue/geographic-segmentation",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Revenue geographic segmentation retrieved successfully",
        kind="fundamentals#revenueGeographicSegmentation",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/revenue/geographic-segmentation",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_institutional_holder_analytics_controller(
    ticker: str,
    year: int,
    quarter: int,
) -> Dict[str, Any]:
    """
    Controller to handle institutional holder analytics data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_institutional_holder_analytics, ticker, year, quarter)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No institutional holder analytics data found for {ticker} ({year} Q{quarter})",
            kind="fundamentals#institutionalHolderAnalytics",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/ownership/institutional-analytics?year={year}&quarter={quarter}",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="Institutional holder analytics retrieved successfully",
        kind="fundamentals#institutionalHolderAnalytics",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/ownership/institutional-analytics?year={year}&quarter={quarter}",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_institutional_positions_summary_controller(
    ticker: str,
    year: int,
    quarter: int,
) -> Dict[str, Any]:
    """
    Controller to handle institutional positions summary data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_institutional_positions_summary, ticker, year, quarter)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No institutional positions summary data found for {ticker} ({year} Q{quarter})",
            kind="fundamentals#institutionalPositionsSummary",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/ownership/institutional-positions?year={year}&quarter={quarter}",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="Institutional positions summary retrieved successfully",
        kind="fundamentals#institutionalPositionsSummary",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/ownership/institutional-positions?year={year}&quarter={quarter}",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_company_notes_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle company notes and bonds data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_company_notes, ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No company notes data found for {ticker}",
            kind="fundamentals#companyNotes",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/company-notes",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Company notes retrieved successfully",
        kind="fundamentals#companyNotes",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/company-notes",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )
