from typing import Optional
from backend.src.utils.logging_config import init_logger
from backend.src.data.user_portfolio_data.fetch_ibkr_holdings import fetch_ibkr_portfolio_positions
from backend.src.data.user_portfolio_data.store_user_positions import store_portfolio_positions
from backend.src.utils.retrieve_user_auth_data import get_user_id_from_email

logger = init_logger(__name__)

def update_user_portfolio_in_db(email: str) -> bool:
    """
    Update user's portfolio in database with latest IBKR holdings data.
    
    Fetches current holdings from IBKR and updates the user_portfolios table
    using upsert logic for the user identified by the given email.
    
    Args:
        email: The user's email address.
        
    Returns:
        bool: True if update was successful, False otherwise.
    """
    logger.info(f"Starting portfolio update for user with email: {email}")

    # Step 1: Get user_id from email
    user_id = get_user_id_from_email(email)
    if not user_id:
        logger.error(f"❌ Failed to find user_id for email: {email}. Update aborted.")
        return False

    # Step 2: Fetch current holdings from IBKR
    latest_positions = fetch_ibkr_portfolio_positions()

    if latest_positions is None:
        logger.error(f"❌ Failed to fetch latest portfolio positions from IBKR for user_id: {user_id}. Update aborted.")
        return False
    
    if not latest_positions:
        logger.warning(f"⚠️ No positions returned from IBKR for user_id: {user_id}. If this is unexpected, please check IBKR connection and account status.")

    logger.info(f"Attempting to store/update portfolio for user_id: '{user_id}'.")
    
    stored_user_id = store_portfolio_positions(
        user_id=user_id, 
        email=email,
        positions_data=latest_positions
    )

    if stored_user_id:
        logger.info(f"✅ Successfully updated portfolio for user_id: {stored_user_id}.")
        return True
    else:
        logger.error(f"❌ Failed to store/update portfolio for user_id: '{user_id}'.")
        return False

if __name__ == '__main__':
    TEST_EMAIL = "michael@laret.com"

    logger.info(f"🚀 Starting portfolio update test for user with email: {TEST_EMAIL}")

    success = update_user_portfolio_in_db(email=TEST_EMAIL)

    if success:
        logger.info(f"✅ Portfolio update test completed successfully for email: {TEST_EMAIL}.")
    else:
        logger.error(f"❌ Portfolio update test failed for email: {TEST_EMAIL}.")

    # Clean up: Disconnect IBKR if necessary (handled by atexit in ib_utils)
    from backend.src.utils.ib_utils import get_ib
    ib_instance = get_ib() 
    if ib_instance and ib_instance.isConnected():
        logger.info("Ensuring IBKR disconnection for script if active.")
        ib_instance.disconnect()
    logger.info("Test finished.") 