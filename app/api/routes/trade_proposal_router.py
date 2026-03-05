"""Trade proposal API routes — list, get, approve, reject."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.api.auth.clerk import get_clerk_user_id
from app.api.controller.trade_proposal import (
    get_proposals_controller,
    get_proposal_by_id_controller,
    approve_proposal_controller,
    reject_proposal_controller,
)

router = APIRouter(prefix="/trade-proposals", tags=["Trade Proposals"])


@router.get("")
async def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status: pending, executed, rejected, failed"),
    proposal_type: Optional[str] = Query(None, description="Filter by type: trade, close_position"),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """List trade proposals for the authenticated user."""
    return await get_proposals_controller(
        clerk_id=clerk_id, status=status, proposal_type=proposal_type,
    )


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get a single trade proposal by ID."""
    return await get_proposal_by_id_controller(
        clerk_id=clerk_id, proposal_id=proposal_id,
    )


@router.patch("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Approve a pending trade proposal and execute the order via SnapTrade."""
    return await approve_proposal_controller(
        clerk_id=clerk_id, proposal_id=proposal_id,
    )


@router.patch("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Reject a pending trade proposal."""
    return await reject_proposal_controller(
        clerk_id=clerk_id, proposal_id=proposal_id,
    )
