"""Broker account controllers — account info, balances, SnapTrade connection."""

from typing import Optional, Dict, Any
from app.repositories.user.account import get_connection_status
from app.services.broker.onboarding import (
    register_snaptrade_user,
    save_snaptrade_account,
    get_snaptrade_connect_url,
)
from app.services.broker.account import (
    get_broker_account,
    get_balances,
)
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


# ════════════════════════════════════════════════════════════
# --> Connection Status
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_connection_status_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Check whether the user has a connected brokerage account (DB-only)."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    status = get_connection_status(clerk_id=clerk_id)

    return ok_envelope(
        message="Connection status retrieved successfully",
        kind="broker#connectionStatus",
        self_link="/api/broker/connection-status",
        payload=status,
    )


# ════════════════════════════════════════════════════════════
# --> SnapTrade Registration & Callback
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def snaptrade_register_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Register a new user with SnapTrade and store credentials."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = register_snaptrade_user(clerk_id=clerk_id)

    return ok_envelope(
        message="SnapTrade user registered successfully",
        kind="broker#snaptradeRegister",
        self_link="/api/broker/snaptrade/register",
        payload=result,
    )


@handle_controller_errors
async def snaptrade_callback_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Fetch and save SnapTrade account after OAuth completion."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = save_snaptrade_account(clerk_id=clerk_id)

    return ok_envelope(
        message="SnapTrade account saved successfully",
        kind="broker#snaptradeCallback",
        self_link="/api/broker/snaptrade/callback",
        payload=result,
    )


# ════════════════════════════════════════════════════════════
# --> SnapTrade Connection
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def snaptrade_connect_controller(
    *,
    clerk_id: str,
    broker: Optional[str] = None,
    custom_redirect: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a SnapTrade connection portal redirect URL (always trade permissions)."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = get_snaptrade_connect_url(
        clerk_id=clerk_id,
        broker=broker,
        custom_redirect=custom_redirect,
    )

    return ok_envelope(
        message="SnapTrade connection URL generated successfully",
        kind="broker#snaptradeConnect",
        self_link="/api/broker/snaptrade/connect",
        payload=result,
    )
