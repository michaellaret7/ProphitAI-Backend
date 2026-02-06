"""User data repository - organized into submodules by domain."""

from app.repositories.user.user import (
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
)

from app.repositories.user.company import (
    add_company,
    assign_all_users_to_company_by_name,
    assign_all_users_to_prophitai,
    set_all_users_to_admin,
    assign_user_to_company_by_id,
)

from app.repositories.user.portfolio import (
    get_user_current_portfolio,
)

from app.repositories.user.watchlist import (
    get_user_watchlists,
    get_watchlist_by_id,
    add_watchlist,
    rename_watchlist,
    delete_watchlist,
    add_watchlist_item,
    delete_watchlist_item,
)
