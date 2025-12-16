from fastapi import HTTPException
from typing import Optional, Dict, Any, List
from app.repositories.user_data import (
    get_user_watchlists,
    get_watchlist_by_id,
    add_watchlist,
    rename_watchlist,
    delete_watchlist,
    add_watchlist_item,
    delete_watchlist_item
)
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.serialize_output import serialize_sqlalchemy_obj

def _format_watchlist_response(watchlist: dict) -> Dict[str, Any]:
    """Format a single watchlist for API response."""
    return {
        "id": watchlist.get("id"),
        "userId": watchlist.get("user_id"),
        "name": watchlist.get("name"),
        "creationDate": watchlist.get("creation_date"),
        "updatedDate": watchlist.get("updated_date"),
        "items": [
            {
                "ticker": item.get("ticker"),
                "priceOnInception": item.get("price_on_inception"),
                "addedAt": item.get("added_at"),
            }
            for item in watchlist.get("items", [])
        ],
    }


def _format_watchlist_item_response(item: dict) -> Dict[str, Any]:
    """Format a watchlist item for API response."""
    return {
        "watchlistId": item.get("watchlist_id"),
        "ticker": item.get("ticker"),
        "priceOnInception": item.get("price_on_inception"),
        "addedAt": item.get("added_at"),
    }


@handle_controller_errors
async def get_user_watchlists_controller(*, user_id: str) -> Dict[str, Any]:
    """Get all watchlists for a user."""
    if not user_id:
        raise ValueError("userId is required")

    watchlists = get_user_watchlists(user_id=user_id)

    return ok_envelope(
        message="Watchlists retrieved successfully",
        kind="watchlists#list",
        self_link=f"/api/watchlists",
        counts={"totalItems": len(watchlists)},
        payload=[_format_watchlist_response(w) for w in watchlists],
    )


@handle_controller_errors
async def get_watchlist_controller(*, watchlist_id: str, user_id: str) -> Dict[str, Any]:
    """Get a single watchlist by ID."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ok_envelope(
        message="Watchlist retrieved successfully",
        kind="watchlists#watchlist",
        resource_id=watchlist.get("id"),
        self_link=f"/api/watchlists/{watchlist_id}",
        payload=_format_watchlist_response(watchlist),
    )


@handle_controller_errors
async def create_watchlist_controller(*, user_id: str, name: str) -> Dict[str, Any]:
    """Create a new watchlist for a user."""
    if not user_id:
        raise ValueError("userId is required")
    if not name:
        raise ValueError("name is required")

    watchlist = add_watchlist(user_id=user_id, name=name)

    return ok_envelope(
        message="Watchlist created successfully",
        kind="watchlists#watchlist",
        resource_id=watchlist.get("id"),
        self_link=f"/api/watchlists/{watchlist.get('id')}",
        status=201,
        payload={
            "id": watchlist.get("id"),
            "userId": watchlist.get("user_id"),
            "name": watchlist.get("name"),
            "creationDate": watchlist.get("creation_date"),
        },
    )


@handle_controller_errors
async def rename_watchlist_controller(
    *, watchlist_id: str, user_id: str, name: str
) -> Dict[str, Any]:
    """Rename an existing watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not name:
        raise ValueError("name is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = rename_watchlist(watchlist_id=watchlist_id, name=name)

    return ok_envelope(
        message="Watchlist renamed successfully",
        kind="watchlists#watchlist",
        resource_id=result.get("id"),
        self_link=f"/api/watchlists/{watchlist_id}",
        payload={
            "id": result.get("id"),
            "name": result.get("name"),
            "updatedDate": result.get("updated_date"),
        },
    )


@handle_controller_errors
async def delete_watchlist_controller(*, watchlist_id: str, user_id: str) -> Dict[str, Any]:
    """Delete a watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    delete_watchlist(watchlist_id=watchlist_id)

    return ok_envelope(
        message="Watchlist deleted successfully",
        kind="watchlists#watchlist",
        resource_id=watchlist_id,
        self_link=f"/api/watchlists/{watchlist_id}",
        payload={},
    )


@handle_controller_errors
async def add_watchlist_item_controller(
    *, watchlist_id: str, user_id: str, ticker: str
) -> Dict[str, Any]:
    """Add a ticker to a watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not ticker:
        raise ValueError("ticker is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    item = add_watchlist_item(
        watchlist_id=watchlist_id,
        ticker=ticker
    )

    return ok_envelope(
        message="Ticker added to watchlist",
        kind="watchlists#item",
        self_link=f"/api/watchlists/{watchlist_id}/items/{item.get('ticker')}",
        status=201,
        payload=_format_watchlist_item_response(item),
    )


@handle_controller_errors
async def delete_watchlist_item_controller(
    *, watchlist_id: str, user_id: str, ticker: str
) -> Dict[str, Any]:
    """Remove a ticker from a watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not ticker:
        raise ValueError("ticker is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    deleted = delete_watchlist_item(watchlist_id=watchlist_id, ticker=ticker)

    if not deleted:
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist")

    return ok_envelope(
        message="Ticker removed from watchlist",
        kind="watchlists#item",
        self_link=f"/api/watchlists/{watchlist_id}/items/{ticker}",
        payload={},
    )
