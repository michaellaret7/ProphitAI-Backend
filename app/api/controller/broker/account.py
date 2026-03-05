"""Broker account controllers — account info, balances, activities, SnapTrade connection."""

from typing import Optional, Dict, Any
from app.repositories.user.account import (
    get_broker_account,
    get_balances,
    get_account_activities,
)
from app.repositories.user.broker import get_snaptrade_connect_url
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


# ════════════════════════════════════════════════════════════
# --> Account Info
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_broker_account_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get full broker account info."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    account = get_broker_account(clerk_id=clerk_id)

    return ok_envelope(
        message="Broker account retrieved successfully",
        kind="broker#account",
        self_link="/api/broker/account",
        payload=account,
    )


@handle_controller_errors
async def get_balances_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get account balances (cash, buying power, equity)."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    balances = get_balances(clerk_id=clerk_id)

    return ok_envelope(
        message="Account balances retrieved successfully",
        kind="broker#balances",
        self_link="/api/broker/account/balances",
        payload=balances,
    )


@handle_controller_errors
async def get_account_activities_controller(
    *,
    clerk_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activity_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get broker account activities."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    activities = get_account_activities(
        clerk_id=clerk_id,
        start_date=start_date,
        end_date=end_date,
        activity_type=activity_type,
    )

    return ok_envelope(
        message="Account activities retrieved successfully",
        kind="broker#activities",
        self_link="/api/broker/account/activities",
        counts={"totalItems": len(activities)},
        payload=activities,
    )


# ════════════════════════════════════════════════════════════
# --> SnapTrade Connection
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def snaptrade_connect_controller(
    *,
    clerk_id: str,
    broker: Optional[str] = None,
    connection_type: Optional[str] = None,
    custom_redirect: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a SnapTrade connection portal redirect URL."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = get_snaptrade_connect_url(
        clerk_id=clerk_id,
        broker=broker,
        connection_type=connection_type,
        custom_redirect=custom_redirect,
    )

    return ok_envelope(
        message="SnapTrade connection URL generated successfully",
        kind="broker#snaptradeConnect",
        self_link="/api/broker/snaptrade/connect",
        payload=result,
    )
