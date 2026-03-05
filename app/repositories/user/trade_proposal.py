"""Trade proposal CRUD and execution repository."""

from typing import Optional
from uuid import UUID

from app.db.core.models.user_data_models import TradeProposal, User
from app.repositories.user.broker import (
    get_snaptrade_broker, resolve_snaptrade_credentials,
)
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


def _execute_trade(broker, proposal: TradeProposal, creds: dict) -> dict:
    """Execute a standard trade proposal via SnapTrade buy/sell.

    Args:
        broker: SnapTradeBroker instance.
        proposal: The TradeProposal ORM record.
        creds: Dict with snaptrade_user_id, snaptrade_user_secret, snaptrade_account_id.
    """
    order_kwargs = {
        "user_id": creds["snaptrade_user_id"],
        "user_secret": creds["snaptrade_user_secret"],
        "account_id": proposal.account_id,
        "symbol": proposal.symbol,
        "order_type": proposal.order_type or "Market",
        "time_in_force": proposal.time_in_force or "Day",
    }
    if proposal.qty is not None:
        order_kwargs["units"] = proposal.qty
    if proposal.notional is not None:
        order_kwargs["notional"] = proposal.notional
    if proposal.limit_price is not None:
        order_kwargs["price"] = proposal.limit_price
    if proposal.stop_price is not None:
        order_kwargs["stop"] = proposal.stop_price

    trade_fn = broker.buy if proposal.side == "buy" else broker.sell
    return trade_fn(**order_kwargs)


def _execute_close_position(broker, proposal: TradeProposal, creds: dict) -> dict:
    """Execute a close_position proposal via SnapTrade sell.

    SnapTrade has no close_position() method, so we:
    1. Fetch current holdings to find the matching position
    2. Calculate units to sell based on qty, percentage, or full close
    3. Execute a sell order

    Args:
        broker: SnapTradeBroker instance.
        proposal: The TradeProposal ORM record.
        creds: Dict with snaptrade_user_id, snaptrade_user_secret, snaptrade_account_id.
    """
    holdings = broker.get_holdings(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=proposal.account_id,
    )

    # Reason: Find the position matching the proposal symbol
    position = None
    for p in holdings.positions:
        if p.ticker.upper() == proposal.symbol.upper():
            position = p
            break

    if position is None:
        raise ValueError(f"No open position found for {proposal.symbol}")

    # Reason: Determine units to sell
    if proposal.qty is not None:
        units = proposal.qty
    elif proposal.percentage is not None:
        units = position.units * (proposal.percentage / 100)
    else:
        units = position.units

    return broker.sell(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=proposal.account_id,
        symbol=proposal.symbol,
        units=units,
        time_in_force="Day",
    )


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
def approve_proposal(
    *,
    clerk_id: str,
    proposal_id: str,
    session=None,
) -> dict:
    """Approve a pending proposal and execute it via SnapTrade.

    Validates ownership and pending status, then dispatches to the
    appropriate execution path based on proposal_type:
    - 'trade': calls broker.buy() / broker.sell()
    - 'close_position': fetches holdings, calculates units, calls broker.sell()

    Updates status to 'executed' on success or 'failed' on error.

    Args:
        clerk_id: Clerk authentication ID.
        proposal_id: The proposal UUID.

    Returns:
        Serialized proposal dict with updated status and order result.

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
        raise ValueError(f"Proposal is already {proposal.status} — only pending proposals can be approved")

    broker = get_snaptrade_broker()
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)

    try:
        if proposal.proposal_type == "close_position":
            result = _execute_close_position(broker, proposal, creds)
        else:
            result = _execute_trade(broker, proposal, creds)

        proposal.status = "executed"
        proposal.broker_order_id = (
            (result.get("brokerage_order_id") or result.get("id"))
            if isinstance(result, dict) else str(result)
        )
        proposal.executed_at = get_current_utc_time()
    except Exception as e:
        proposal.status = "failed"
        proposal.error_message = str(e)

    session.flush()
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
