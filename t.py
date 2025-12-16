"""
Test script for watchlist creation and adding positions.
Tests the create watchlist endpoint and adds 5 random positions for herman@laret.com
"""
import random
from app.repositories.user_data import (
    get_all_user_data,
    add_watchlist,
    add_watchlist_item,
    get_user_watchlists,
)

# Random tickers to add
RANDOM_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"]


def test_create_watchlist_and_add_positions():
    """Create a watchlist for herman@laret.com and add 5 random positions."""
    email = "herman@laret.com"

    # Step 1: Get user by email
    print(f"Looking up user: {email}")
    user_data = get_all_user_data(email=email)

    if not user_data:
        print(f"ERROR: User {email} not found in database")
        return

    user_id = user_data["id"]
    print(f"Found user: {user_data['first_name']} {user_data['last_name']} (ID: {user_id})")

    # Step 2: Create a new watchlist
    watchlist_name = "Test Watchlist"
    print(f"\nCreating watchlist: {watchlist_name}")

    watchlist = add_watchlist(user_id=user_id, name=watchlist_name)
    watchlist_id = watchlist["id"]
    print(f"Created watchlist with ID: {watchlist_id}")

    # Step 3: Add 5 random tickers
    selected_tickers = random.sample(RANDOM_TICKERS, 5)
    print(f"\nAdding {len(selected_tickers)} random tickers: {selected_tickers}")

    for ticker in selected_tickers:
        item = add_watchlist_item(watchlist_id=watchlist_id, ticker=ticker)
        print(f"  Added {ticker} - Price on inception: ${item.get('price_on_inception', 'N/A')}")

    # Step 4: Verify by fetching the watchlist
    print("\nVerifying watchlists for user...")
    watchlists = get_user_watchlists(user_id=user_id)

    for wl in watchlists:
        if wl["id"] == watchlist_id:
            print(f"\nWatchlist '{wl['name']}' (ID: {wl['id']})")
            print(f"  Created: {wl['creation_date']}")
            print(f"  Items ({len(wl['items'])}):")
            for item in wl["items"]:
                print(f"    - {item['ticker']}: ${item.get('price_on_inception', 'N/A')} (added: {item['added_at']})")

    print("\nTest completed successfully!")




