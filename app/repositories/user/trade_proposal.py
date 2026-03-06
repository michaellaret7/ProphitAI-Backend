"""Trade proposal CRUD repository — pure DB access."""

import json
from typing import Optional
from uuid import UUID

from app.db.core.models.user_data_models import TradeProposal, User
from app.utils.decorators.database import with_session, with_transaction
from app.utils.time_utils import get_current_utc_time


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _proposal_to_dict(proposal: TradeProposal) -> dict:
    """Serialize a TradeProposal ORM instance to a plain dict."""
    return {
        "id": str(proposal.id),
        "user_id": str(proposal.user_id),
        "account_id": proposal.account_id,
        "proposal_type": proposal.proposal_type,
        "symbol": proposal.symbol,
        "side": proposal.side,
        "qty": proposal.qty,
        "percentage": proposal.percentage,
        "notional": proposal.notional,
        "order_type": proposal.order_type,
        "limit_price": proposal.limit_price,
        "stop_price": proposal.stop_price,
        "time_in_force": proposal.time_in_force,
        "agent_reasoning": proposal.agent_reasoning,
        "legs": json.loads(proposal.legs) if proposal.legs else None,
        "status": proposal.status,
        "broker_order_id": proposal.broker_order_id,
        "error_message": proposal.error_message,
        "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
        "updated_at": proposal.updated_at.isoformat() if proposal.updated_at else None,
        "executed_at": proposal.executed_at.isoformat() if proposal.executed_at else None,
        "rejected_at": proposal.rejected_at.isoformat() if proposal.rejected_at else None,
    }


@with_session('user')
def get_internal_user_id(*, clerk_id: str, session=None) -> str:
    """Return the internal UUID string for a given Clerk ID.

    Args:
        clerk_id: Clerk authentication ID.

    Raises:
        ValueError: If user not found.
    """
    return str(_resolve_user_id(clerk_id, session))


def _resolve_user_id(clerk_id: str, session) -> UUID:
    """Resolve a Clerk ID to the internal user UUID.

    Args:
        clerk_id: Clerk authentication ID.
        session: Active SQLAlchemy session.

    Raises:
        ValueError: If user not found.
    """
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        raise ValueError("User not found")
    return user.id


# ════════════════════════════════════════════════════════════
# --> CRUD
# ════════════════════════════════════════════════════════════

@with_transaction('user')
def create_proposal(
    *,
    user_id: str,
    account_id: str,
    symbol: str,
    side: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "Day",
    agent_reasoning: Optional[str] = None,
    session=None,
) -> dict:
    """Insert a new trade proposal with status 'pending'.

    Args:
        user_id: Internal user UUID (string).
        account_id: SnapTrade broker account ID.
        symbol: Ticker symbol.
        side: 'buy' or 'sell'.
        qty: Share quantity (mutually exclusive with notional).
        notional: Dollar amount (mutually exclusive with qty).
        order_type: Order type — Market, Limit, Stop, or StopLimit.
        limit_price: Limit price for Limit/StopLimit orders.
        stop_price: Stop trigger price for Stop/StopLimit orders.
        time_in_force: How long the order stays active (Day, GTC, FOK, IOC).
        agent_reasoning: LLM explanation for why this trade was proposed.

    Returns:
        Serialized proposal dict.
    """
    proposal = TradeProposal(
        user_id=user_id,
        account_id=account_id,
        proposal_type="trade",
        symbol=symbol.upper(),
        side=side,
        qty=qty,
        notional=notional,
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        agent_reasoning=agent_reasoning,
        status="pending",
    )
    session.add(proposal)
    session.flush()
    return _proposal_to_dict(proposal)


@with_transaction('user')
def create_close_proposal(
    *,
    user_id: str,
    account_id: str,
    symbol: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
    agent_reasoning: Optional[str] = None,
    session=None,
) -> dict:
    """Insert a close_position proposal with status 'pending'.

    Args:
        user_id: Internal user UUID (string).
        account_id: SnapTrade broker account ID.
        symbol: Ticker symbol of the position to close.
        qty: Number of shares to close. Omit for full close.
        percentage: Percentage of position to close (e.g. 50.0 for 50%).
        agent_reasoning: LLM explanation for why this close was proposed.

    Returns:
        Serialized proposal dict.
    """
    proposal = TradeProposal(
        user_id=user_id,
        account_id=account_id,
        proposal_type="close_position",
        symbol=symbol.upper(),
        side="sell",
        qty=qty,
        percentage=percentage,
        time_in_force="Day",
        agent_reasoning=agent_reasoning,
        status="pending",
    )
    session.add(proposal)
    session.flush()
    return _proposal_to_dict(proposal)


@with_transaction('user')
def create_options_proposal(
    *,
    user_id: str,
    account_id: str,
    osi_symbol: str,
    side: str,
    contracts: int,
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    time_in_force: str = "Day",
    agent_reasoning: Optional[str] = None,
    session=None,
) -> dict:
    """Insert a single-leg options trade proposal with status 'pending'.

    Args:
        user_id: Internal user UUID (string).
        account_id: SnapTrade broker account ID.
        osi_symbol: OSI-format option symbol (e.g. 'AAPL260620C00200000').
        side: Options action — buy_to_open, sell_to_close, sell_to_open, buy_to_close.
        contracts: Number of contracts.
        order_type: Market or Limit.
        limit_price: Limit price for Limit orders.
        time_in_force: Day or GTC.
        agent_reasoning: LLM explanation for why this trade was proposed.

    Returns:
        Serialized proposal dict.
    """
    proposal = TradeProposal(
        user_id=user_id,
        account_id=account_id,
        proposal_type="options_trade",
        symbol=osi_symbol,
        side=side,
        qty=contracts,
        order_type=order_type,
        limit_price=limit_price,
        time_in_force=time_in_force,
        agent_reasoning=agent_reasoning,
        status="pending",
    )
    session.add(proposal)
    session.flush()
    return _proposal_to_dict(proposal)


@with_transaction('user')
def create_multi_leg_options_proposal(
    *,
    user_id: str,
    account_id: str,
    legs: list[dict],
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "Day",
    agent_reasoning: Optional[str] = None,
    session=None,
) -> dict:
    """Insert a multi-leg options trade proposal with status 'pending'.

    Args:
        user_id: Internal user UUID (string).
        account_id: SnapTrade broker account ID.
        legs: List of leg dicts, each with 'symbol' (OSI), 'action', 'units'.
        order_type: Market or Limit.
        limit_price: Net limit price for Limit orders.
        stop_price: Stop trigger price.
        time_in_force: Day or GTC.
        agent_reasoning: LLM explanation for why this trade was proposed.

    Returns:
        Serialized proposal dict.
    """
    # Reason: Store underlying ticker from first leg for display purposes
    from app.brokers.snaptrade.utils import _OSI_SPLIT
    first_match = _OSI_SPLIT.match(legs[0]["symbol"])
    display_symbol = first_match.group(1) if first_match else legs[0]["symbol"]

    proposal = TradeProposal(
        user_id=user_id,
        account_id=account_id,
        proposal_type="options_multi_leg",
        symbol=display_symbol,
        side="multi_leg",
        legs=json.dumps(legs),
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        agent_reasoning=agent_reasoning,
        status="pending",
    )
    session.add(proposal)
    session.flush()
    return _proposal_to_dict(proposal)


@with_session('user')
def get_proposals_for_user(
    *,
    clerk_id: str,
    status_filter: Optional[str] = None,
    proposal_type: Optional[str] = None,
    session=None,
) -> list[dict]:
    """Get all trade proposals for a user, optionally filtered by status and type.

    Args:
        clerk_id: Clerk authentication ID.
        status_filter: Optional status to filter by (pending, executed, rejected, failed).
        proposal_type: Optional type to filter by ('trade', 'close_position').

    Returns:
        List of serialized proposal dicts ordered by created_at DESC.
    """
    user_id = _resolve_user_id(clerk_id, session)
    query = session.query(TradeProposal).filter(TradeProposal.user_id == user_id)
    if status_filter:
        query = query.filter(TradeProposal.status == status_filter)
    if proposal_type:
        query = query.filter(TradeProposal.proposal_type == proposal_type)
    proposals = query.order_by(TradeProposal.created_at.desc()).all()
    return [_proposal_to_dict(p) for p in proposals]


@with_session('user')
def get_proposal_by_id(
    *,
    clerk_id: str,
    proposal_id: str,
    session=None,
) -> dict:
    """Get a single trade proposal by ID, verifying ownership.

    Args:
        clerk_id: Clerk authentication ID.
        proposal_id: The proposal UUID.

    Returns:
        Serialized proposal dict.

    Raises:
        ValueError: If proposal not found or not owned by user.
    """
    user_id = _resolve_user_id(clerk_id, session)
    proposal = session.query(TradeProposal).filter(
        TradeProposal.id == proposal_id,
        TradeProposal.user_id == user_id,
    ).first()
    if not proposal:
        raise ValueError("Trade proposal not found")
    return _proposal_to_dict(proposal)


@with_transaction('user')
def reject_proposal(
    *,
    clerk_id: str,
    proposal_id: str,
    session=None,
) -> dict:
    """Reject a pending proposal.

    Args:
        clerk_id: Clerk authentication ID.
        proposal_id: The proposal UUID.

    Returns:
        Serialized proposal dict with status set to 'rejected'.

    Raises:
        ValueError: If proposal not found, not owned, or not pending.
    """
    user_id = _resolve_user_id(clerk_id, session)
    proposal = session.query(TradeProposal).filter(
        TradeProposal.id == proposal_id,
        TradeProposal.user_id == user_id,
    ).first()

    if not proposal:
        raise ValueError("Trade proposal not found")
    if proposal.status != "pending":
        raise ValueError(f"Proposal is already {proposal.status} — only pending proposals can be rejected")

    proposal.status = "rejected"
    proposal.rejected_at = get_current_utc_time()
    session.flush()
    return _proposal_to_dict(proposal)
