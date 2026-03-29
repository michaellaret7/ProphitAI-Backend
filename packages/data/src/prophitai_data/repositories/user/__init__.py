"""User data repository — organized into submodules by domain."""

# ── Account (CRUD) ───────────────────────────────────────────
from prophitai_data.repositories.user.account import (
    get_all_user_data,
    get_all_user_data_by_id,
    get_all_user_data_by_clerk_id,
    get_user_basic_info,
    email_exists,
    add_user,
    update_user_clerk_id,
    update_user_fields,
    update_user_by_clerk_id,
    delete_user_by_clerk_id,
    get_connection_status,
)

# ── Watchlists ────────────────────────────────────────────────
from prophitai_data.repositories.user.watchlist import (
    get_user_watchlists,
    get_watchlist_by_id,
    add_watchlist,
    rename_watchlist,
    delete_watchlist,
    add_watchlist_item,
    delete_watchlist_item,
)
