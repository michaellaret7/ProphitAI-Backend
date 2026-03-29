"""Broker connection controllers — list and remove SnapTrade authorizations."""

from typing import Dict, Any

from prophitai_api.services.broker.connections import list_connections, remove_connection
from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_api.utils.decorators import handle_controller_errors


# ════════════════════════════════════════════════════════════
# --> Connection Management
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def list_connections_controller(*, clerk_id: str) -> Dict[str, Any]:
    """List all SnapTrade brokerage connections for the authenticated user."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    connections = list_connections(clerk_id=clerk_id)

    return ok_envelope(
        message="Connections retrieved successfully",
        kind="broker#connections",
        self_link="/api/broker/connections",
        payload=connections,
    )


@handle_controller_errors
async def remove_connection_controller(
    *, clerk_id: str, authorization_id: str,
) -> Dict[str, Any]:
    """Remove a SnapTrade brokerage connection."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not authorization_id:
        raise ValueError("authorization_id is required")

    remove_connection(clerk_id=clerk_id, authorization_id=authorization_id)

    return ok_envelope(
        message="Connection removed successfully",
        kind="broker#connectionRemoved",
        self_link=f"/api/broker/connections/{authorization_id}",
    )
