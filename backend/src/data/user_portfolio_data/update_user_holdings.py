from typing import Optional
from backend.src.utils.logging_config import init_logger
from backend.src.data.user_portfolio_data.fetch_ibkr_holdings import fetch_ibkr_portfolio_positions
from backend.src.data.user_portfolio_data.store_user_positions import store_portfolio_positions, TABLE_NAME
from backend.src.utils.database import get_cursor

logger = init_logger(__name__)

def update_user_portfolio_in_db(user_identifier: str, is_user_id: bool = False) -> bool:
    """
    Update user's portfolio in database with latest IBKR holdings data.
    
    Fetches current holdings from IBKR and updates the user_portfolios table
    using upsert logic to replace existing positions for the specified user.
    
    Args:
        user_identifier: The user's name (str) or user_id (str).
        is_user_id: True if user_identifier is a user_id, False if it's a user_name (default).
        
    Returns:
        bool: True if update was successful, False otherwise.
    """
    logger.info(f"Starting portfolio update for user_identifier: {user_identifier}")

    # Step 1: Fetch current holdings from IBKR
    latest_positions = fetch_ibkr_portfolio_positions()

    if latest_positions is None:
        logger.error(f"❌ Failed to fetch latest portfolio positions from IBKR for {user_identifier}. Update aborted.")
        return False
    
    if not latest_positions:
        logger.warning(f"⚠️ No positions returned from IBKR for {user_identifier}. If this is unexpected, please check IBKR connection and account status.")
        # We can still proceed to effectively clear out positions if the user truly has none,
        # or store_portfolio_positions will handle it if it's meant to update specific records.
        # However, to be safe and align with "replace only the rows with the same user name or id",
        # we should first ensure the user exists if we are to clear their specific holdings.

    # Step 2: Determine user_id and user_name
    user_id_to_use: Optional[str] = None
    user_name_to_use: Optional[str] = None

    if is_user_id:
        user_id_to_use = user_identifier
        # Optionally, we could try to fetch user_name if needed, but store_portfolio_positions can handle user_id alone
        # For now, if only user_id is given, user_name in the DB might not be updated unless store_portfolio_positions does it.
        # The current store_portfolio_positions expects user_name.
        # Let's retrieve the user_name if user_id is provided.
        try:
            with get_cursor(dbname='user_data') as cursor:
                cursor.execute(f"SELECT DISTINCT user_name FROM {TABLE_NAME} WHERE user_id = %s LIMIT 1", (user_id_to_use,))
                result = cursor.fetchone()
                if result:
                    user_name_to_use = result[0]
                else:
                    logger.error(f"🚨 No user_name found for user_id: {user_id_to_use}. Cannot proceed with update by user_id if user_name is unknown and required by store_portfolio_positions.")
                    # Depending on store_user_positions strictness, this might be an issue.
                    # The existing store_user_positions always requires user_name.
                    return False 
        except Exception as e:
            logger.error(f"🚨 Error fetching user_name for user_id {user_id_to_use}: {e}", exc_info=True)
            return False
    else:
        user_name_to_use = user_identifier
        # user_id will be handled by store_portfolio_positions (either found or created)

    if not user_name_to_use: # Should only happen if is_user_id was true and lookup failed
        logger.error(f"User name could not be determined for identifier: {user_identifier}. Update aborted.")
        return False

    # Step 3: Store/Update the fetched positions in the database
    # The store_portfolio_positions function handles the upsert logic.
    # It will update existing rows based on the primary key (user_id, account, symbol, secType)
    # or insert new ones if they don't exist for that user.
    # If latest_positions is empty, it should effectively update/remove previous holdings
    # for this user *if* store_portfolio_positions handles empty lists by deleting.
    # The current store_portfolio_positions will simply log "No positions data provided"
    # and not change the database if latest_positions is empty.
    # This might not be the desired "replace" behavior if "replace" means "delete old if new is empty".
    # For now, we assume store_portfolio_positions with an empty list means "do nothing".
    # If the intention is to delete all user's positions if IBKR returns an empty list,
    # then explicit delete logic for that user_id would be needed here *before* calling store.

    logger.info(f"Attempting to store/update portfolio for user_name: '{user_name_to_use}' (user_id to be handled by store: {user_id_to_use if user_id_to_use else 'will be looked up/created'}).")
    
    stored_user_id = store_portfolio_positions(
        user_name=user_name_to_use, 
        positions_data=latest_positions,
        user_id=user_id_to_use # Pass user_id if known
    )

    if stored_user_id:
        logger.info(f"✅ Successfully updated portfolio for user_name: '{user_name_to_use}' with user_id: {stored_user_id}.")
        return True
    else:
        logger.error(f"❌ Failed to store/update portfolio for user_name: '{user_name_to_use}'.")
        return False

if __name__ == '__main__':
    TEST_USER_NAME = "test_user_beta_two" # Choose a test user name

    logger.info(f"🚀 Starting portfolio update test for user: {TEST_USER_NAME}")

    success = update_user_portfolio_in_db(user_identifier=TEST_USER_NAME, is_user_id=False)
    
    # Example: Update by user_id (first, you'd need to get a user_id)
    # initial_user_id = store_portfolio_positions(user_name="temp_user_for_id", positions_data=[])
    # if initial_user_id:
    #     logger.info(f"Created/retrieved temp_user_for_id with ID: {initial_user_id} for testing update by ID.")
    #     success_by_id = update_user_portfolio_in_db(user_identifier=initial_user_id, is_user_id=True)
    #     logger.info(f"Update by user_id ({initial_user_id}) success: {success_by_id}")
    # else:
    #     logger.error("Could not get an ID for temp_user_for_id to test update_by_id.")


    if success:
        logger.info(f"✅ Portfolio update test completed successfully for user: {TEST_USER_NAME}.")
    else:
        logger.error(f"❌ Portfolio update test failed for user: {TEST_USER_NAME}.")

    # Clean up: Disconnect IBKR if necessary (handled by atexit in ib_utils)
    from backend.src.utils.ib_utils import get_ib
    ib_instance = get_ib() 
    if ib_instance and ib_instance.isConnected():
        logger.info("Ensuring IBKR disconnection for script if active.")
        ib_instance.disconnect()
    logger.info("Test finished.") 