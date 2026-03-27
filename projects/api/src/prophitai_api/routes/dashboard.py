"""Dashboard routes — single composite endpoint for all dashboard data."""

from fastapi import APIRouter, Depends
from prophitai_api.auth.clerk import get_clerk_user_id
from prophitai_api.controllers.dashboard import get_dashboard_controller

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard(clerk_id: str = Depends(get_clerk_user_id)):
    """Return aggregated dashboard data (account, positions, orders, news, etc.)."""
    return await get_dashboard_controller(clerk_id=clerk_id)
