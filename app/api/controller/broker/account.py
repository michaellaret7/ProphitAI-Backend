"""Broker account and funding controllers."""

from typing import Optional, Dict, Any
from app.repositories.user.account import (
    create_user_with_broker_account,
    get_broker_account,
    get_buying_power,
    get_cash_balance,
    get_equity,
    get_account_activities,
)
from app.repositories.user.funding import (
    link_bank_account,
    get_ach_relationships,
    delete_ach_relationship,
    deposit,
    withdraw,
    get_transfers,
    cancel_transfer,
    instant_deposit,
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
async def get_buying_power_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get broker account buying power."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    buying_power = get_buying_power(clerk_id=clerk_id)

    return ok_envelope(
        message="Buying power retrieved successfully",
        kind="broker#buyingPower",
        self_link="/api/broker/account/buying-power",
        payload={"buyingPower": buying_power},
    )


@handle_controller_errors
async def get_cash_balance_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get broker account cash balance."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    cash = get_cash_balance(clerk_id=clerk_id)

    return ok_envelope(
        message="Cash balance retrieved successfully",
        kind="broker#cash",
        self_link="/api/broker/account/cash",
        payload={"cash": cash},
    )


@handle_controller_errors
async def get_equity_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get broker account equity."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    equity = get_equity(clerk_id=clerk_id)

    return ok_envelope(
        message="Equity retrieved successfully",
        kind="broker#equity",
        self_link="/api/broker/account/equity",
        payload={"equity": equity},
    )


@handle_controller_errors
async def get_account_activities_controller(
    *, clerk_id: str, activity_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get broker account activities."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    activities = get_account_activities(
        clerk_id=clerk_id, activity_type=activity_type,
    )

    return ok_envelope(
        message="Account activities retrieved successfully",
        kind="broker#activities",
        self_link="/api/broker/account/activities",
        counts={"totalItems": len(activities)},
        payload=activities,
    )


@handle_controller_errors
async def create_broker_account_controller(
    *, clerk_id: str, signup_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new brokerage account (KYC onboarding)."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    # Reason: inject clerk_id so the repo can link the broker account to the user
    signup_data["clerk_id"] = clerk_id

    result = create_user_with_broker_account(signup_data=signup_data)

    return ok_envelope(
        message="Broker account created successfully",
        kind="broker#account",
        resource_id=result.get("broker_account_id"),
        self_link="/api/broker/account",
        status=201,
        payload=result,
    )


# ════════════════════════════════════════════════════════════
# --> ACH Relationships
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def link_bank_account_controller(
    *, clerk_id: str, bank_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Link a bank account via ACH."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = link_bank_account(clerk_id=clerk_id, bank_data=bank_data)

    return ok_envelope(
        message="Bank account linked successfully",
        kind="broker#achRelationship",
        self_link="/api/broker/ach",
        status=201,
        payload=result,
    )


@handle_controller_errors
async def get_ach_relationships_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get all linked bank accounts."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    relationships = get_ach_relationships(clerk_id=clerk_id)

    return ok_envelope(
        message="ACH relationships retrieved successfully",
        kind="broker#achRelationships",
        self_link="/api/broker/ach",
        counts={"totalItems": len(relationships)},
        payload=relationships,
    )


@handle_controller_errors
async def delete_ach_relationship_controller(
    *, clerk_id: str, relationship_id: str
) -> Dict[str, Any]:
    """Remove a bank connection."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not relationship_id:
        raise ValueError("relationshipId is required")

    delete_ach_relationship(clerk_id=clerk_id, relationship_id=relationship_id)

    return ok_envelope(
        message="ACH relationship deleted successfully",
        kind="broker#achRelationship",
        resource_id=relationship_id,
        self_link=f"/api/broker/ach/{relationship_id}",
        payload={},
    )


# ════════════════════════════════════════════════════════════
# --> Transfers
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def deposit_controller(
    *, clerk_id: str, relationship_id: str, amount: float
) -> Dict[str, Any]:
    """Deposit money from linked bank into brokerage account."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if amount <= 0:
        raise ValueError("amount must be greater than 0")

    result = deposit(
        clerk_id=clerk_id, relationship_id=relationship_id, amount=amount,
    )

    return ok_envelope(
        message="Deposit initiated successfully",
        kind="broker#transfer",
        self_link="/api/broker/transfers",
        status=201,
        payload=result,
    )


@handle_controller_errors
async def withdraw_controller(
    *, clerk_id: str, relationship_id: str, amount: float
) -> Dict[str, Any]:
    """Withdraw money from brokerage account to linked bank."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if amount <= 0:
        raise ValueError("amount must be greater than 0")

    result = withdraw(
        clerk_id=clerk_id, relationship_id=relationship_id, amount=amount,
    )

    return ok_envelope(
        message="Withdrawal initiated successfully",
        kind="broker#transfer",
        self_link="/api/broker/transfers",
        status=201,
        payload=result,
    )


@handle_controller_errors
async def get_transfers_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get all transfers for a user."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    transfers = get_transfers(clerk_id=clerk_id)

    return ok_envelope(
        message="Transfers retrieved successfully",
        kind="broker#transfers",
        self_link="/api/broker/transfers",
        counts={"totalItems": len(transfers)},
        payload=transfers,
    )


@handle_controller_errors
async def cancel_transfer_controller(
    *, clerk_id: str, transfer_id: str
) -> Dict[str, Any]:
    """Cancel a pending transfer."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not transfer_id:
        raise ValueError("transferId is required")

    cancel_transfer(clerk_id=clerk_id, transfer_id=transfer_id)

    return ok_envelope(
        message="Transfer cancelled successfully",
        kind="broker#transfer",
        resource_id=transfer_id,
        self_link=f"/api/broker/transfers/{transfer_id}",
        payload={},
    )


# ════════════════════════════════════════════════════════════
# --> Instant Transfers (Firm Journal)
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def instant_deposit_controller(
    *, clerk_id: str, amount: float
) -> Dict[str, Any]:
    """Journal cash from the firm funding account to the user instantly."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if amount <= 0:
        raise ValueError("amount must be greater than 0")

    result = instant_deposit(clerk_id=clerk_id, amount=amount)

    return ok_envelope(
        message="Instant deposit completed successfully",
        kind="broker#instantTransfer",
        self_link="/api/broker/transfers/instant-deposit",
        status=201,
        payload=result,
    )
