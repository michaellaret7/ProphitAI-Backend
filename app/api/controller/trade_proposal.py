"""Trade proposal controllers — list, get, approve, reject."""

from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.api.response_envelope import ok_envelope
from app.repositories.user.trade_proposal import (
    get_proposals_for_user,
    get_proposal_by_id,
    approve_proposal,
    reject_proposal,
)
from app.utils.decorators.api_decorators import handle_controller_errors


# ════════════════════════════════════════════════════════════
# --> Controllers
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_proposals_controller(
    *, clerk_id: str, status: Optional[str] = None, proposal_type: Optional[str] = None,
) -> Dict[str, Any]:
    """List trade proposals for the authenticated user."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    proposals = get_proposals_for_user(
        clerk_id=clerk_id, status_filter=status, proposal_type=proposal_type,
    )

    return ok_envelope(
        message="Trade proposals retrieved successfully",
        kind="trade#proposals",
        self_link="/api/trade-proposals",
        counts={"totalItems": len(proposals)},
        payload=proposals,
    )


@handle_controller_errors
async def get_proposal_by_id_controller(
    *, clerk_id: str, proposal_id: str,
) -> Dict[str, Any]:
    """Get a single trade proposal by ID."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not proposal_id:
        raise ValueError("proposalId is required")

    proposal = get_proposal_by_id(clerk_id=clerk_id, proposal_id=proposal_id)

    return ok_envelope(
        message="Trade proposal retrieved successfully",
        kind="trade#proposal",
        resource_id=proposal_id,
        self_link=f"/api/trade-proposals/{proposal_id}",
        payload=proposal,
    )


@handle_controller_errors
async def approve_proposal_controller(
    *, clerk_id: str, proposal_id: str,
) -> Dict[str, Any]:
    """Approve a pending trade proposal and execute on Alpaca."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not proposal_id:
        raise ValueError("proposalId is required")

    result = approve_proposal(clerk_id=clerk_id, proposal_id=proposal_id)

    if result["status"] == "failed":
        raise HTTPException(
            status_code=502,
            detail=f"Broker execution failed: {result.get('error_message', 'unknown error')}",
        )

    return ok_envelope(
        message="Trade proposal approved and executed",
        kind="trade#proposal",
        resource_id=proposal_id,
        self_link=f"/api/trade-proposals/{proposal_id}",
        payload=result,
    )


@handle_controller_errors
async def reject_proposal_controller(
    *, clerk_id: str, proposal_id: str,
) -> Dict[str, Any]:
    """Reject a pending trade proposal."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not proposal_id:
        raise ValueError("proposalId is required")

    result = reject_proposal(clerk_id=clerk_id, proposal_id=proposal_id)

    return ok_envelope(
        message="Trade proposal rejected",
        kind="trade#proposal",
        resource_id=proposal_id,
        self_link=f"/api/trade-proposals/{proposal_id}",
        payload=result,
    )
