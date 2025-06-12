from typing import Optional
from backend.src.utils.logging_config import init_logger, patch_print_for_logging
from backend.src.data.user_portfolio_data.fetch_ibkr_holdings import fetch_ibkr_portfolio_positions
from backend.src.data.user_portfolio_data.store_user_positions import store_portfolio_positions
from backend.src.utils.ib_utils import get_ib
from backend.src.utils.retrieve_user_auth_data import get_user_id_from_email

logger = init_logger(__name__)

def retrieve_and_store_portfolio_data(email: str) -> Optional[str]:
    """
    Complete workflow to fetch and store portfolio data from IBKR.
    
    Executes the full process of fetching portfolio positions from Interactive Brokers
    and storing them in the database with proper cleanup and error handling.
    
    Args:
        email: The email address of the user whose portfolio to fetch and store.
        
    Returns:
        Optional[str]: user_id if successful, None if operation failed.
    """
    logger.info(f"🚀 Starting portfolio retrieval and storage for user with email: '{email}'...")
    
    # Get user_id from email
    user_id = get_user_id_from_email(email)
    if not user_id:
        logger.error(f"❌ Could not retrieve user_id for email: {email}. Aborting workflow.")
        return None
    
    logger.info(f"Found user_id: {user_id} for email: {email}")

    try:
        # Fetch portfolio positions from IBKR
        logger.info("Fetching portfolio positions from IBKR...")
        positions = fetch_ibkr_portfolio_positions()

        if positions is not None:
            logger.info(f"Fetched {len(positions)} positions from IBKR.")
            
            # Store positions in database
            logger.info(f"Attempting to store positions for user_id: {user_id}...")
            stored_user_id = store_portfolio_positions(user_id, email, positions)

            if stored_user_id:
                logger.info(f"✅ Positions stored successfully under user_id: {stored_user_id}")
                return stored_user_id
            else:
                logger.error(f"❌ Failed to store positions for user_id: {user_id}")
                return None
        else:
            logger.warning("⚠️ No positions fetched from IBKR. Cannot store data.")
            return None
            
    except Exception as e:
        logger.error(f"🚨 Error in portfolio retrieval and storage workflow for user_id '{user_id}': {e}", exc_info=True)
        return None
    
    finally:
        # Ensure IBKR connection cleanup
        try:
            ib_instance = get_ib()
            if ib_instance and ib_instance.isConnected():
                logger.info("Ensuring IBKR disconnection after portfolio retrieval.")
                ib_instance.disconnect()
        except Exception as e:
            logger.warning(f"⚠️ Error during IBKR cleanup: {e}")

if __name__ == '__main__':
    # Test the workflow function
    patch_print_for_logging()
    logger.info("🧪 Testing retrieve_and_store_portfolio_data workflow...")
    
    test_email = "michael@laret.com"
    
    result = retrieve_and_store_portfolio_data(test_email)
    
    if result:
        logger.info(f"✅ Workflow completed successfully. User ID: {result}")
    else:
        logger.error("❌ Workflow failed.")
    
    logger.info("Test finished for retrieve_and_store_portfolio_data.py.") 