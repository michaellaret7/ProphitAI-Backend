"""Broker proposal services — trade proposal approval and execution."""

import json

from prophitai_data.clients.snaptrade.credentials import get_snaptrade_broker, resolve_snaptrade_credentials
from prophitai_data.session.decorators import with_transaction
from prophitai_shared.time_utils import get_current_utc_time
from prophitai_data.db.models.user import TradeProposal


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

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
    portfolio = broker.get_portfolio(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=proposal.account_id,
    )

    # Reason: Find the position matching the proposal symbol
    position = None
    for p in portfolio.equity_positions:
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


def _execute_options_trade(broker, proposal: TradeProposal, creds: dict) -> dict:
    """Execute a single-leg options trade proposal.

    Args:
        broker: SnapTradeBroker instance.
        proposal: The TradeProposal ORM record.
        creds: Dict with snaptrade_user_id, snaptrade_user_secret, snaptrade_account_id.
    """
    # Reason: Dispatch to the correct broker method based on side
    dispatch = {
        "buy_to_open": broker.buy_to_open,
        "sell_to_close": broker.sell_to_close,
        "sell_to_open": broker.sell_to_open,
        "buy_to_close": broker.buy_to_close,
    }
    trade_fn = dispatch[proposal.side]

    kwargs = {
        "user_id": creds["snaptrade_user_id"],
        "user_secret": creds["snaptrade_user_secret"],
        "account_id": proposal.account_id,
        "osi_symbol": proposal.symbol,
        "units": int(proposal.qty),
        "order_type": proposal.order_type or "Market",
        "time_in_force": proposal.time_in_force or "Day",
    }
    if proposal.limit_price is not None:
        kwargs["price"] = proposal.limit_price

    return trade_fn(**kwargs)


def _execute_multi_leg_trade(broker, proposal: TradeProposal, creds: dict) -> dict:
    """Execute a multi-leg options trade proposal.

    Args:
        broker: SnapTradeBroker instance.
        proposal: The TradeProposal ORM record (legs stored as JSON in proposal.legs).
        creds: Dict with snaptrade_user_id, snaptrade_user_secret, snaptrade_account_id.
    """
    legs = json.loads(proposal.legs)

    kwargs = {
        "user_id": creds["snaptrade_user_id"],
        "user_secret": creds["snaptrade_user_secret"],
        "account_id": proposal.account_id,
        "legs": legs,
        "order_type": proposal.order_type or "Market",
        "time_in_force": proposal.time_in_force or "Day",
    }
    if proposal.limit_price is not None:
        kwargs["limit_price"] = proposal.limit_price
    if proposal.stop_price is not None:
        kwargs["stop_price"] = proposal.stop_price

    return broker.place_multi_leg_order(**kwargs)


# ════════════════════════════════════════════════════════════
# --> Proposal Execution
# ════════════════════════════════════════════════════════════

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
    from prophitai_data.repositories.user.trade_proposal import _resolve_user_id, _proposal_to_dict

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

    # Reason: Dispatch to the correct executor based on proposal_type
    executor_map = {
        "trade": _execute_trade,
        "close_position": _execute_close_position,
        "options_trade": _execute_options_trade,
        "options_multi_leg": _execute_multi_leg_trade,
    }

    try:
        executor = executor_map.get(proposal.proposal_type, _execute_trade)
        result = executor(broker, proposal, creds)

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
