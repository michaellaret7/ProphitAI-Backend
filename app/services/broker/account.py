"""Broker account services — balances, equity, and buying power."""

from typing import Optional, List, Dict, Any

from app.repositories.user.broker import get_snaptrade_broker, resolve_snaptrade_credentials


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _first_balance(clerk_id: str) -> Dict[str, Any]:
    """Return the first balance dict from SnapTrade, or empty dict."""
    balances = get_balances(clerk_id)
    return balances[0] if balances else {}


# ════════════════════════════════════════════════════════════
# --> Account Info
# ════════════════════════════════════════════════════════════

def get_broker_account(clerk_id: str) -> Dict[str, Any]:
    """
    Get full broker account info via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        Dict with account details (number, name, type, status, balances, etc.)
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_account_details(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
    )


def get_balances(clerk_id: str) -> List[Dict[str, Any]]:
    """
    Get account balances (cash, buying power, equity) via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        List of balance dicts with currency, cash, buying_power fields
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_balances(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
    )


def get_equity(clerk_id: str) -> Optional[float]:
    """Get total account equity (cash + position market values)."""
    from app.services.broker.trading import get_positions
    cash = get_cash_balance(clerk_id) or 0
    positions = get_positions(clerk_id)
    total_mv = sum(float(p.get("market_value") or 0) for p in positions) if positions else 0.0
    return round(cash + total_mv, 2)


def get_buying_power(clerk_id: str) -> Optional[float]:
    """Get buying power from account balances via SnapTrade."""
    return _first_balance(clerk_id).get("buying_power")


def get_cash_balance(clerk_id: str) -> Optional[float]:
    """Get cash balance from account balances via SnapTrade."""
    return _first_balance(clerk_id).get("cash")


