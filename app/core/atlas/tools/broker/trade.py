"""SnapTrade trade proposal tool for agent framework."""

from typing import Annotated, Optional, Literal

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.repositories.user.broker import resolve_snaptrade_credentials
from app.repositories.user.trade_proposal import create_proposal
from app.core.atlas.tools.broker.helpers import resolve_user_id_by_email 


# ================================
# --> Tools
# ================================

@agent_tool(name="propose_trade")
def propose_trade(
    email: str,
    symbol: str,
    side: Literal['buy', 'sell'],
    reasoning: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    order_type: Annotated[str, Param(enum=['Market', 'Limit', 'Stop', 'StopLimit'])] = "Market",
    time_in_force: Annotated[str, Param(enum=['Day', 'GTC', 'FOK', 'IOC'])] = "Day",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> str:
    """
    Submit a trade proposal for user approval. The trade is NOT executed immediately —
    it is stored as a pending proposal that the user must approve or reject
    from the trade proposals page.

    IMPORTANT: Do NOT call this tool until the user has explicitly confirmed the trade
    idea in chat. You must first research the trade thoroughly, present your analysis
    and trade idea verbally (symbol, side, qty, reasoning), and wait for the user
    to say 'yes', 'go ahead', or otherwise confirm. Only then call this tool.

    Order types:
    - Market: executes at current market price (default)
    - Limit: executes at limit_price or better
    - Stop: triggers a market order when stop_price is reached
    - StopLimit: triggers a limit order at limit_price when stop_price is reached

    You must provide exactly one of qty or notional, not both.

    Args:
        email: The user's email address (used to resolve broker credentials)
        symbol: Ticker symbol to trade (e.g. 'AAPL', 'MSFT')
        side: Trade direction — 'buy' or 'sell'
        reasoning: Your explanation for why this trade is being proposed.
            Must clearly explain the rationale so the user can make an informed decision.
        qty: Number of shares to trade. Fractional shares supported (e.g. 0.5).
            Mutually exclusive with notional.
        notional: Dollar amount to trade (e.g. 1000.0 buys $1000 worth).
            Mutually exclusive with qty. Only for market orders.
        order_type: Order type — Market, Limit, Stop, or StopLimit.
        time_in_force: How long the order stays active.
            - Day: Cancelled at end of trading day (default)
            - GTC: Good-til-cancelled
            - FOK: Fill-or-kill (fill entirely or cancel)
            - IOC: Immediate-or-cancel (fill what you can, cancel rest)
        limit_price: Limit price for Limit/StopLimit orders.
        stop_price: Stop trigger price for Stop/StopLimit orders.

    Returns:
        Confirmation that the trade proposal was created and is pending user approval.

    Examples:
        propose_trade(email="user@example.com", symbol="AAPL",
                      side="buy", qty=10, reasoning="Strong earnings beat, momentum play")
        >>> "Trade proposal created: BUY 10 shares of AAPL — pending user approval"

    Raises:
        Exception: If the proposal could not be created
    """
    if qty is None and notional is None:
        return error_response("Either qty or notional must be provided")
    if qty is not None and notional is not None:
        return error_response("Cannot specify both qty and notional")

    try:
        creds = resolve_snaptrade_credentials(email=email)
        user_id = resolve_user_id_by_email(email)

        proposal = create_proposal(
            user_id=user_id,
            account_id=creds["snaptrade_account_id"],
            symbol=symbol,
            side=side,
            qty=qty,
            notional=notional,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            agent_reasoning=reasoning,
        )

        # Reason: Build a clear summary for the agent's response
        amount_str = f"{qty} shares" if qty else f"${notional}"
        return success_response(
            f"Trade proposal created: {side.upper()} {amount_str} of {symbol.upper()} "
            f"— pending user approval. Proposal ID: {proposal['id']}"
        )
    except Exception as e:
        # Reason: Strip raw SQL from DB errors to avoid leaking schema details
        msg = str(e)
        if "psycopg2" in msg or "sqlalchemy" in msg.lower():
            msg = msg.split("\n")[0]
        return error_response(f"Failed to create trade proposal: {msg}")
