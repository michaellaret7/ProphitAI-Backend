"""User data repository — organized into submodules by domain."""

# ── Account (CRUD + broker account) ──────────────────────────
from app.repositories.user.account import (
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
    create_user_with_broker_account,
    get_broker_account,
    get_buying_power,
    get_cash_balance,
    get_equity,
    get_account_activities,
)

# ── Trading (orders + positions) ─────────────────────────────
from app.repositories.user.trading import (
    buy,
    sell,
    get_orders,
    get_order_by_id,
    cancel_order,
    cancel_all_orders,
    get_positions,
    get_position,
    close_position,
    close_all_positions,
)

# ── Funding (ACH + transfers) ────────────────────────────────
from app.repositories.user.funding import (
    link_bank_account,
    get_ach_relationships,
    delete_ach_relationship,
    deposit,
    withdraw,
    get_transfers,
    cancel_transfer,
)

# ── Portfolio ─────────────────────────────────────────────────
from app.repositories.user.portfolio import (
    get_user_current_portfolio,
    get_portfolio_history,
)

# ── Watchlists ────────────────────────────────────────────────
from app.repositories.user.watchlist import (
    get_user_watchlists,
    get_watchlist_by_id,
    add_watchlist,
    rename_watchlist,
    delete_watchlist,
    add_watchlist_item,
    delete_watchlist_item,
)
