"""Controllers for market data endpoints (M&A, FX, indexes)."""

import asyncio
from typing import Dict, Any, Optional

from fastapi import HTTPException

from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_data.clients.fmp import FMP_API_DATA


@handle_controller_errors
async def get_mergers_acquisitions_latest_controller(
    page: int = 0,
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Controller to handle latest M&A data retrieval
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    # FMP API uses requests.get() which is synchronous and blocks during network I/O
    data = await asyncio.to_thread(fmp_api.get_mergers_acquisitions_latest, page=page, limit=limit)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve M&A data from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Latest M&A transactions retrieved successfully",
        kind="macro#mergersAcquisitionsLatest",
        self_link=f"/api/macro/mergers-acquisitions/latest?page={page}&limit={limit}",
        counts={"totalItems": len(items), "currentItemCount": len(items), "startIndex": page * limit},
        payload=items,
    )


@handle_controller_errors
async def get_mergers_acquisitions_search_controller(
    name: str,
) -> Dict[str, Any]:
    """
    Controller to handle M&A search by company name
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    # FMP API uses requests.get() which is synchronous and blocks during network I/O
    data = await asyncio.to_thread(fmp_api.get_mergers_acquisitions_search, name=name)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve M&A data from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message=f"M&A transactions for '{name}' retrieved successfully",
        kind="macro#mergersAcquisitionsSearch",
        resource_id=name,
        self_link=f"/api/macro/mergers-acquisitions/search?name={name}",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


async def get_fx_historical_prices_controller(
    pair: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle FX historical prices retrieval
    """
    fmp_api = FMP_API_DATA()
    data = await asyncio.to_thread(fmp_api.get_forex_historical_prices, pair=pair, from_date=from_date, to_date=to_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve FX historical prices from FMP API")

    return ok_envelope(
        message="FX historical prices retrieved successfully",
        kind="macro#fxHistoricalPrices",
        resource_id=pair,
        self_link=f"/api/macro/fx/historical-prices?pair={pair}&fromDate={from_date}&endDate={to_date}",
        counts={"totalItems": len(data["historical"]), "currentItemCount": len(data["historical"])},
        payload=data["historical"],
    )


@handle_controller_errors
async def get_index_list_controller() -> Dict[str, Any]:
    """
    Controller to retrieve list of all available market indexes.

    Returns:
        Response envelope with list of indexes (symbol, name, exchange, currency)
    """
    fmp_api = FMP_API_DATA()
    data = await asyncio.to_thread(fmp_api.get_index_list)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve index list from FMP API")

    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Index list retrieved successfully",
        kind="macro#indexList",
        resource_id="all",
        self_link="/api/macro/index/list",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )
