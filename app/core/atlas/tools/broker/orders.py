"""SnapTrade order and account tools for agent framework."""

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.repositories.user.broker import get_snaptrade_broker, resolve_snaptrade_credentials
from typing import Annotated, Optional, Literal


# ================================
# --> Account Tools
# ================================

@agent_tool(name="get_order_impact")
def get_order_impact(
    email: str,
    symbol: str,
    action: Literal['BUY', 'SELL'],
    units: float,
    order_type: Annotated[str, Param(enum=['Market', 'Limit', 'Stop', 'StopLimit'])] = "Market",
    time_in_force: Annotated[str, Param(enum=['Day', 'GTC', 'FOK', 'IOC'])] = "Day",
    price: Optional[float] = None,
    stop: Optional[float] = None,
) -> str:
    """
    Preview the estimated impact of an order before placing it. Returns
    projected cost, commission, buying power effect, and whether the account
    has sufficient funds. Use this to validate a trade idea before proposing it.

    Args:
        email: User's email address
        symbol: Ticker symbol (e.g. 'AAPL')
        action: Trade direction — BUY or SELL
        units: Number of shares
        order_type: Order type (Market, Limit, Stop, StopLimit)
        time_in_force: How long the order stays active (Day, GTC, FOK, IOC)
        price: Limit price (required for Limit/StopLimit orders)
        stop: Stop trigger price (required for Stop/StopLimit orders)

    Returns:
        Dict with estimated trade cost, commission, buying power impact,
        and remaining buying power after the trade

    Examples:
        get_order_impact(email="user@example.com", symbol="AAPL",
                         action="BUY", units=100)
        >>> {"trade": {"symbol": "AAPL", ...}, "buying_power_effect": -17525.00, ...}

    Raises:
        Exception: If the order would be rejected or credentials are invalid
    """
    try:
        creds = resolve_snaptrade_credentials(email=email)
        broker = get_snaptrade_broker()
        result = broker.get_order_impact(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
            symbol=symbol,
            action=action,
            units=units,
            order_type=order_type,
            time_in_force=time_in_force,
            price=price,
            stop=stop,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to get order impact for {symbol}: {str(e)}")


# ================================
# --> Tools
# ================================

@agent_tool(name="get_orders")
def get_orders(
    email: str,
    state: Literal['all', 'open', 'executed'] = "open",
    days: Annotated[Optional[int], Param(min_val=1, max_val=20)] = None,
) -> str:
    """
    Get orders for the user's brokerage account filtered by state.

    Args:
        email: User's email address
        state: Filter orders by state.
            - open: Only unfilled/partially filled orders (default)
            - executed: Only completed orders
            - all: All orders regardless of state
        days: Number of days to look back (1-20). If omitted, uses broker default.

    Returns:
        List of order dicts with symbol, side, quantity, type, status,
        filled quantity, and timestamps

    Examples:
        get_orders(email="user@example.com", state="open")
        >>> [{"symbol": "AAPL", "action": "BUY", "units": 10, ...}]

    Raises:
        Exception: If credentials are invalid or API call fails
    """
    try:
        creds = resolve_snaptrade_credentials(email=email)
        broker = get_snaptrade_broker()
        result = broker.get_orders(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
            state=state,
            days=days,
        )
        if not result:
            return success_response(f"No {state} orders found")
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to get orders: {str(e)}")


@agent_tool(name="cancel_order")
def cancel_order(
    email: str,
    brokerage_order_id: str,
) -> str:
    """
    Cancel a specific open order by its brokerage order ID.

    Args:
        email: User's email address
        brokerage_order_id: The brokerage-assigned order ID to cancel

    Returns:
        Confirmation that the order was cancelled

    Examples:
        cancel_order(email="user@example.com", brokerage_order_id="abc-123")
        >>> "Order abc-123 cancelled successfully"

    Raises:
        Exception: If the order does not exist, is already filled, or credentials are invalid
    """
    try:
        creds = resolve_snaptrade_credentials(email=email)
        broker = get_snaptrade_broker()
        broker.cancel_order(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
            brokerage_order_id=brokerage_order_id,
        )
        return success_response(f"Order {brokerage_order_id} cancelled successfully")
    except Exception as e:
        return error_response(f"Failed to cancel order {brokerage_order_id}: {str(e)}")


@agent_tool(name="get_quotes")
def get_quotes(
    email: str,
    symbols: str,
) -> str:
    """
    Get real-time quotes for one or more ticker symbols.

    Args:
        email: User's email address
        symbols: Comma-separated ticker symbols (e.g. 'AAPL,MSFT,GOOG')

    Returns:
        List of quote dicts with bid/ask prices, last price, and volume

    Examples:
        get_quotes(email="user@example.com", symbols="AAPL,MSFT")
        >>> [{"symbol": "AAPL", "last": 185.50, "bid": 185.49, "ask": 185.51, ...}]

    Raises:
        Exception: If symbols are invalid or credentials are incorrect
    """
    try:
        creds = resolve_snaptrade_credentials(email=email)
        broker = get_snaptrade_broker()
        result = broker.get_quotes(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
            symbols=symbols,
        )
        if not result:
            return success_response(f"No quotes found for: {symbols}")
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to get quotes for {symbols}: {str(e)}")
