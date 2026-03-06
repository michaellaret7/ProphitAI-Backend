"""SnapTrade portfolio tools for agent framework."""

from typing import Optional

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.repositories.user.broker import resolve_snaptrade_credentials, get_snaptrade_broker
from app.repositories.user.trade_proposal import create_close_proposal
from app.core.atlas.tools.broker.helpers import resolve_user_id_by_email

# ================================
# --> Constants
# ================================

_EXCLUDE_POSITION_FIELDS = {"snaptrade_symbol_id", "figi_code", "fractional_units", "cash_equivalent"}

# ================================
# --> Tools
# ================================

@agent_tool(name="get_positions")
def get_positions(
    email: str,
) -> str:
    """
    Get all open positions (equities and options) for a user's brokerage account.

    Args:
        email: The user's email address

    Returns:
        Dict with 'equity_positions' and 'option_positions' lists.
        Equity positions have ticker, units, price, market_value, open_pnl, etc.
        Option positions have underlying_ticker, strike_price, expiration_date, option_type, units, price, etc.

    Examples:
        get_positions(email="user@example.com")
        >>> {"equity_positions": [...], "option_positions": [...]}

    Raises:
        Exception: If credentials cannot be resolved or API call fails
    """
    try:
        creds = resolve_snaptrade_credentials(email=email)
        broker = get_snaptrade_broker()

        portfolio = broker.get_portfolio(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
        )

        return success_response({
            "equity_positions": [p.model_dump(exclude=_EXCLUDE_POSITION_FIELDS) for p in portfolio.equity_positions],
            "option_positions": [op.model_dump() for op in portfolio.option_positions],
        })
    except TypeError as e:
        return error_response(f"Missing or invalid arguments: {e}")
    except Exception as e:
        msg = str(e)
        if "psycopg2" in msg or "sqlalchemy" in msg.lower():
            msg = msg.split("\n")[0]
        return error_response(f"Failed to get positions for {email}: {msg}")

@agent_tool(name="close_position")
def close_position(
    email: str,
    symbol: str,
    reasoning: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
) -> str:
    """
    Submit a close-position proposal for user approval. The position is NOT
    closed immediately — it is stored as a pending proposal that the user must
    approve or reject from the trade proposals page.

    IMPORTANT: Do NOT call this tool until the user has explicitly confirmed
    the close in chat. You must first present your analysis and reasoning,
    and wait for the user to say 'yes', 'go ahead', or otherwise confirm.

    Omit both qty and percentage to propose closing the entire position.
    Provide exactly one of qty or percentage for a partial close.

    Args:
        email: The user's email address
        symbol: Ticker symbol of the position to close (e.g. 'AAPL')
        reasoning: Your explanation for why this position should be closed.
            Must clearly explain the rationale so the user can make an informed decision.
        qty: Number of shares to sell. Omit for full close.
        percentage: Percentage of position to close (e.g. 50.0 for 50%). Omit for full close.

    Returns:
        Confirmation that the close-position proposal was created and is pending.

    Examples:
        close_position(email="user@example.com", symbol="AAPL",
                       reasoning="Position hit stop-loss target")
        >>> "Close position proposal created: CLOSE 100% of AAPL — pending user approval"

    Raises:
        ValueError: If both qty and percentage are provided
        Exception: If the proposal could not be created
    """
    try:
        if qty is not None and percentage is not None:
            return error_response("Cannot specify both qty and percentage")

        if percentage is not None and not (0 < percentage <= 100):
            return error_response("percentage must be between 0 and 100")

        creds = resolve_snaptrade_credentials(email=email)
        user_id = resolve_user_id_by_email(email)

        proposal = create_close_proposal(
            user_id=user_id,
            account_id=creds["snaptrade_account_id"],
            symbol=symbol,
            qty=qty,
            percentage=percentage,
            agent_reasoning=reasoning,
        )

        # Reason: Build a clear summary for the agent's response
        if qty is not None:
            amount_str = f"{qty} shares of"
        elif percentage is not None:
            amount_str = f"{percentage}% of"
        else:
            amount_str = "100% of"

        return success_response(
            f"Close position proposal created: CLOSE {amount_str} {symbol.upper()} "
            f"— pending user approval. Proposal ID: {proposal['id']}"
        )
    except TypeError as e:
        return error_response(f"Missing or invalid arguments: {e}")
    except Exception as e:
        msg = str(e)
        if "psycopg2" in msg or "sqlalchemy" in msg.lower():
            msg = msg.split("\n")[0]
        return error_response(f"Failed to create close position proposal: {msg}")
