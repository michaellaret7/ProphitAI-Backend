"""Broker connection services — list and remove SnapTrade authorizations."""

from typing import List, Dict

from prophitai_data.clients.snaptrade.credentials import (
    resolve_snaptrade_auth,
    get_snaptrade_broker,
    clear_snaptrade_account,
)


def list_connections(clerk_id: str) -> List[Dict]:
    """
    List all SnapTrade brokerage connections for a user.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        List of connection/authorization dicts from SnapTrade
    """
    creds = resolve_snaptrade_auth(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.list_connections(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
    )


def remove_connection(clerk_id: str, authorization_id: str) -> None:
    """
    Delete a SnapTrade brokerage connection and clear the local account ID.

    Args:
        clerk_id: Clerk authentication ID
        authorization_id: SnapTrade authorization ID to delete
    """
    creds = resolve_snaptrade_auth(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    broker.remove_connection(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        authorization_id=authorization_id,
    )
    # Reason: connection is gone, so the stored account ID is stale
    clear_snaptrade_account(clerk_id=clerk_id)
