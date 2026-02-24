from app.core.atlas.tools_v2.decorator import agent_tool, Param
from typing import Annotated
from app.brokers.alpaca_broker.broker import ProphitBroker
from app.core.atlas.tools_v2.responses import success_response, error_response

@agent_tool(name="account_info")
def account_info(
    account_id: str,
) -> str:
    """
    Query the account information for the given account ID.
    
    Args:
        account_id: The ID of the account to get the account information for
    
    Returns:
        A dictionary containing the account information for the given account ID
    
    Examples:
        account_info(account_id="d27aa8c2-5931-499b-bdfa-05c47b07ad70")
        >>> {
            "account_id": "d27aa8c2-5931-499b-bdfa-05c47b07ad70",
            "status": "ACTIVE",
            "cash": 10000,
            "equity": 10000,
            "buying_power": 10000,
            "portfolio_value": 10000,
        }

    Raises:
        ValueError: If the account ID is not valid
    """
    
    broker = ProphitBroker(sandbox=True)

    try:
        account = broker.get_account(account_id)
        return success_response(account)
    except Exception as e:
        return error_response(f"Failed to get account information for {account_id}: {str(e)}. Try again with a different account ID.")

@agent_tool(name="account_activities")
def account_activities(
    account_id: str,
    activity_type: Annotated[str, Param(enum=['FILL', 'CSD', 'CSW', 'DIV', 'JNLC'])],
) -> str:
    """
    Query the account activities for the given account ID.

    Args:
        account_id: The ID of the account to get the account activities for
        activity_type: The type of activity to filter by. Options:
            - FILL: Order fills (buys/sells). Returns qty, price, symbol, side.
                Example: {"qty": "10.0", "price": "80.22", "symbol": "GM", "side": "OrderSide.BUY"}
            - CSD: Cash deposits into the account. Returns net_amount (positive).
                Example: {"net_amount": "10000.0", "date": "2026-02-23"}
            - CSW: Cash withdrawals from the account. Returns net_amount (negative).
                Example: {"net_amount": "-5000.0", "date": "2026-02-23"}
            - DIV: Dividend payments received. Returns net_amount, symbol.
                Example: {"net_amount": "25.50", "symbol": "AAPL", "date": "2026-02-23"}
            - JNLC: Journal entries (cash transfers between accounts). Returns net_amount.
                Example: {"net_amount": "1000.0", "date": "2026-02-23"}

    Returns:
        A list of activity dicts, each containing: id, activity_type, date, qty, price, symbol, side, net_amount.
        Fields not applicable to the activity type will be None.

    Examples:
        account_activities(account_id="d27aa8c2-5931-499b-bdfa-05c47b07ad70", activity_type="FILL")
        >>> [{"id": "20260223::a033a19b", "activity_type": "FILL", "qty": "10.0", "price": "80.22", "symbol": "GM", "side": "OrderSide.BUY", "net_amount": None},]

        account_activities(account_id="d27aa8c2-5931-499b-bdfa-05c47b07ad70", activity_type="CSD")
        >>> [{"id": "20260223::7c73b4c3", "activity_type": "CSD", "date": "2026-02-23", "net_amount": "10000.0", "symbol": None},]

    Raises:
        Exception: If the account ID is invalid or activities cannot be retrieved
    """
    
    broker = ProphitBroker(sandbox=True)

    try:
        activities = broker.get_account_activities(account_id, activity_type)

        return success_response(activities)
    
    except Exception as e:
        return error_response(f"Failed to get account activities for {account_id}: {str(e)}. Try again with a different account ID.")

