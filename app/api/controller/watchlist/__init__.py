"""Watchlist controller functions."""

from .operations import (
    get_user_watchlists_controller,
    get_watchlist_controller,
    create_watchlist_controller,
    rename_watchlist_controller,
    delete_watchlist_controller,
    add_watchlist_item_controller,
    delete_watchlist_item_controller,
)
from .crud import (
    get_watchlist_metrics_controller,
    get_watchlist_charts_controller,
)

__all__ = [
    # Operations
    "get_user_watchlists_controller",
    "get_watchlist_controller",
    "create_watchlist_controller",
    "rename_watchlist_controller",
    "delete_watchlist_controller",
    "add_watchlist_item_controller",
    "delete_watchlist_item_controller",
    # Data
    "get_watchlist_metrics_controller",
    "get_watchlist_charts_controller",
]
