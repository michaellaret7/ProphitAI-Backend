"""SnapTrade options trade proposal tools for agent framework."""

import re
from typing import Annotated, Optional, Literal

from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools.broker.helpers import resolve_user_id_by_email
from app.repositories.user.broker import resolve_snaptrade_credentials
from app.repositories.user.trade_proposal import (
    create_options_proposal,
    create_multi_leg_options_proposal,
)

# Reason: Reuse the same regex the broker layer uses for OSI validation
_OSI_PATTERN = re.compile(r"^[A-Z0-9.\-]+\d{6}[CP]\d{8}$")

MULTI_LEG_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "OSI option symbol (e.g. 'AAPL260620C00200000')",
            },
            "action": {
                "type": "string",
                "enum": ["buy_to_open", "sell_to_open", "buy_to_close", "sell_to_close"],
                "description": "Options action for this leg",
            },
            "units": {
                "type": "integer",
                "minimum": 1,
                "description": "Number of contracts for this leg",
            },
        },
        "required": ["symbol", "action", "units"],
        "additionalProperties": False,
    },
    "minItems": 2,
    "description": "List of option legs. Each leg has an OSI symbol, action, and number of contracts.",
}


# ================================
# --> Tools
# ================================

@agent_tool(name="propose_options_trade")
def propose_options_trade(
    email: str,
    osi_symbol: str,
    side: Literal['buy_to_open', 'sell_to_close', 'sell_to_open', 'buy_to_close'],
    contracts: Annotated[int, Param(min_val=1)],
    reasoning: str,
    order_type: Annotated[str, Param(enum=['Market', 'Limit'])] = "Market",
    limit_price: Optional[float] = None,
    time_in_force: Annotated[str, Param(enum=['Day', 'GTC'])] = "Day",
) -> str:
    """
    Submit a single-leg options trade proposal for user approval. The trade is NOT
    executed immediately — it is stored as a pending proposal that the user must
    approve or reject from the trade proposals page.

    IMPORTANT: Do NOT call this tool until the user has explicitly confirmed the trade
    idea in chat. You must first present your analysis and wait for confirmation.

    The osi_symbol must be in OSI format: ROOT + YYMMDD + C/P + 8-digit strike.
    Example: AAPL260620C00200000 = AAPL June 20 2026 $200 Call

    You must provide limit_price when order_type is 'Limit'.

    Examples:
        propose_options_trade(email="user@example.com", osi_symbol="AAPL260620C00200000",
                              side="buy_to_open", contracts=5,
                              reasoning="Bullish earnings play, buying June calls")
        >>> "Options proposal created: BUY_TO_OPEN 5x AAPL260620C00200000 — pending user approval"

    Raises:
        Exception: If the proposal could not be created
    """
    if not _OSI_PATTERN.match(osi_symbol):
        return error_response(
            f"Invalid OSI symbol format: '{osi_symbol}'. "
            "Expected format: ROOT + YYMMDD + C/P + 8-digit strike (e.g. AAPL260620C00200000)"
        )

    if order_type == "Limit" and limit_price is None:
        return error_response("limit_price is required for Limit orders")

    try:
        creds = resolve_snaptrade_credentials(email=email)
        user_id = resolve_user_id_by_email(email)

        proposal = create_options_proposal(
            user_id=user_id,
            account_id=creds["snaptrade_account_id"],
            osi_symbol=osi_symbol,
            side=side,
            contracts=contracts,
            order_type=order_type,
            limit_price=limit_price,
            time_in_force=time_in_force,
            agent_reasoning=reasoning,
        )

        return success_response(
            f"Options proposal created: {side.upper()} {contracts}x {osi_symbol} "
            f"— pending user approval. Proposal ID: {proposal['id']}"
        )
    except Exception as e:
        msg = str(e)
        if "psycopg2" in msg or "sqlalchemy" in msg.lower():
            msg = msg.split("\n")[0]
        return error_response(f"Failed to create options proposal: {msg}")


@agent_tool(name="propose_multi_leg_options_trade")
def propose_multi_leg_options_trade(
    email: str,
    legs: Annotated[list, Schema(MULTI_LEG_SCHEMA)],
    reasoning: str,
    order_type: Annotated[str, Param(enum=['Market', 'Limit'])] = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: Annotated[str, Param(enum=['Day', 'GTC'])] = "Day",
) -> str:
    """
    Submit a multi-leg options trade proposal (spreads, straddles, iron condors, etc.)
    for user approval. The trade is NOT executed immediately — it is stored as a pending
    proposal that the user must approve or reject from the trade proposals page.

    IMPORTANT: Do NOT call this tool until the user has explicitly confirmed the trade
    idea in chat. You must first present your analysis and wait for confirmation.

    Each leg must have:
    - symbol: OSI format option symbol (ROOT + YYMMDD + C/P + 8-digit strike)
    - action: buy_to_open, sell_to_open, buy_to_close, or sell_to_close
    - units: number of contracts (>= 1)

    You must provide at least 2 legs. Provide limit_price when order_type is 'Limit'.

    Examples:
        propose_multi_leg_options_trade(
            email="user@example.com",
            legs=[
                {"symbol": "AAPL260620C00200000", "action": "buy_to_open", "units": 5},
                {"symbol": "AAPL260620C00210000", "action": "sell_to_open", "units": 5},
            ],
            reasoning="Bull call spread on AAPL — capped risk, defined reward"
        )

    Raises:
        Exception: If the proposal could not be created
    """
    if len(legs) < 2:
        return error_response("Multi-leg orders require at least 2 legs")

    # Reason: Validate each leg's OSI symbol format
    for i, leg in enumerate(legs):
        if not _OSI_PATTERN.match(leg.get("symbol", "")):
            return error_response(
                f"Invalid OSI symbol in leg {i + 1}: '{leg.get('symbol', '')}'. "
                "Expected format: ROOT + YYMMDD + C/P + 8-digit strike"
            )

    if order_type == "Limit" and limit_price is None:
        return error_response("limit_price is required for Limit orders")

    try:
        creds = resolve_snaptrade_credentials(email=email)
        user_id = resolve_user_id_by_email(email)

        proposal = create_multi_leg_options_proposal(
            user_id=user_id,
            account_id=creds["snaptrade_account_id"],
            legs=legs,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            agent_reasoning=reasoning,
        )

        leg_summary = ", ".join(
            f"{leg['action'].upper()} {leg['units']}x {leg['symbol']}" for leg in legs
        )
        return success_response(
            f"Multi-leg options proposal created: [{leg_summary}] "
            f"— pending user approval. Proposal ID: {proposal['id']}"
        )
    except Exception as e:
        msg = str(e)
        if "psycopg2" in msg or "sqlalchemy" in msg.lower():
            msg = msg.split("\n")[0]
        return error_response(f"Failed to create multi-leg options proposal: {msg}")
