"""Trade proposal CRUD and execution repository."""

from typing import Optional
from uuid import UUID

from app.db.core.models.user_data_models import TradeProposal, User
from app.repositories.user.broker import get_broker
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
        "limit_price": proposal.limit_price,
        "stop_price": proposal.stop_price,
        "trail_price": proposal.trail_price,
        "trail_percent": proposal.trail_percent,
        "take_profit": proposal.take_profit,
        "stop_loss": proposal.stop_loss,
        "stop_loss_limit": proposal.stop_loss_limit,
        "order_class": proposal.order_class,
        "time_in_force": proposal.time_in_force,
        "agent_reasoning": proposal.agent_reasoning,
        "status": proposal.status,
        "alpaca_order_id": proposal.alpaca_order_id,
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


def _execute_trade(broker, proposal: TradeProposal) -> dict:
    """Execute a standard trade proposal via broker buy/sell."""
    order_kwargs = {
        "account_id": proposal.account_id,
        "symbol": proposal.symbol,
        "qty": proposal.qty,
        "notional": proposal.notional,
        "limit_price": proposal.limit_price,
        "stop_price": proposal.stop_price,
        "trail_price": proposal.trail_price,
        "trail_percent": proposal.trail_percent,
        "take_profit": proposal.take_profit,
        "stop_loss": proposal.stop_loss,
        "stop_loss_limit": proposal.stop_loss_limit,
        "order_class": proposal.order_class,
        "time_in_force": proposal.time_in_force,
    }
    # Reason: Strip None values so broker defaults aren't overridden
    order_kwargs = {k: v for k, v in order_kwargs.items() if v is not None}
    trade_fn = broker.buy if proposal.side == "buy" else broker.sell
    return trade_fn(**order_kwargs)


def _execute_close_position(broker, proposal: TradeProposal) -> dict:
    """Execute a close_position proposal via broker.close_position()."""
    close_kwargs = {
        "account_id": proposal.account_id,
        "symbol": proposal.symbol,
    }
    if proposal.qty is not None:
        close_kwargs["qty"] = proposal.qty
    if proposal.percentage is not None:
        close_kwargs["percentage"] = proposal.percentage
    return broker.close_position(**close_kwargs)


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
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    trail_price: Optional[float] = None,
    trail_percent: Optional[float] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
    order_class: Optional[str] = None,
    time_in_force: str = "day",
    agent_reasoning: Optional[str] = None,
    session=None,
) -> dict:
    """Insert a new trade proposal with status 'pending'.

    Args:
        user_id: Internal user UUID (string).
        account_id: Alpaca broker account ID.
        symbol: Ticker symbol.
        side: 'buy' or 'sell'.
        qty: Share quantity (mutually exclusive with notional).
        notional: Dollar amount (mutually exclusive with qty).
        limit_price: Limit price for limit/stop-limit orders.
        stop_price: Stop trigger price.
        trail_price: Dollar offset for trailing stop.
        trail_percent: Percentage offset for trailing stop.
        take_profit: Take-profit limit price for bracket orders.
        stop_loss: Stop-loss trigger price for bracket orders.
        stop_loss_limit: Stop-loss limit price for bracket orders.
        order_class: Order class (simple, bracket, oco, oto).
        time_in_force: How long the order stays active.
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
        limit_price=limit_price,
        stop_price=stop_price,
        trail_price=trail_price,
        trail_percent=trail_percent,
        take_profit=take_profit,
        stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit,
        order_class=order_class,
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
        account_id: Alpaca broker account ID.
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
        time_in_force="day",
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
    """Approve a pending proposal and execute it on Alpaca.

    Validates ownership and pending status, then dispatches to the
    appropriate broker method based on proposal_type:
    - 'trade': calls broker.buy() / broker.sell()
    - 'close_position': calls broker.close_position()

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

    broker = get_broker()

    try:
        if proposal.proposal_type == "close_position":
            result = _execute_close_position(broker, proposal)
        else:
            result = _execute_trade(broker, proposal)

        proposal.status = "executed"
        proposal.alpaca_order_id = result.get("id") if isinstance(result, dict) else str(result)
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
