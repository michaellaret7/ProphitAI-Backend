from typing import Optional
from src.utils.logging_config import init_logger, patch_print_for_logging
from src.data.user_portfolio_data.fetch_ibkr_holdings import fetch_ibkr_portfolio_positions
from data.user_portfolio_data.store_user_positions import store_portfolio_positions
from src.utils.ib_utils import get_ib

logger = init_logger(__name__)

def retrieve_and_store_portfolio_data(user_name: str, user_id: Optional[str] = None) -> Optional[str]:
    """
    Complete workflow to fetch portfolio positions from IBKR and store them in the database.
    
    Args:
        user_name: Name of the user whose portfolio to fetch and store
        user_id: Optional specific user ID to use. If not provided, will use existing or generate new one
    
    Returns:
        user_id if successful, None if failed
    """
    logger.info(f"🚀 Starting portfolio retrieval and storage for user: '{user_name}'...")
    
    try:
        # Fetch portfolio positions from IBKR
        logger.info("Fetching portfolio positions from IBKR...")
        test_positions = fetch_ibkr_portfolio_positions()

        if test_positions is not None:
            logger.info(f"Fetched {len(test_positions)} positions from IBKR.")
            
            # Store positions in database
            logger.info(f"Attempting to store positions for user_name: {user_name}...")
            generated_user_id = store_portfolio_positions(user_name, test_positions, user_id=user_id)

            if generated_user_id:
                logger.info(f"✅ Positions stored successfully under user_id: {generated_user_id}")
                
                # Verify that the returned ID matches provided ID (if one was provided)
                if user_id and generated_user_id == user_id:
                    logger.info(f"✅ Confirmed that the provided user_id '{user_id}' was used.")
                elif user_id and generated_user_id != user_id:
                    logger.warning(f"⚠️ The returned user_id '{generated_user_id}' does not match the provided id '{user_id}'.")
                
                return generated_user_id
            else:
                logger.error(f"❌ Failed to store positions for user_name: {user_name}")
                return None
        else:
            logger.warning("⚠️ No positions fetched from IBKR. Cannot store data.")
            return None
            
    except Exception as e:
        logger.error(f"🚨 Error in portfolio retrieval and storage workflow for user '{user_name}': {e}", exc_info=True)
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
    
    test_user_name = "test_user_beta_two"
    import uuid
    test_user_id = str(uuid.uuid4())
    # test_user_id = "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    
    result = retrieve_and_store_portfolio_data(test_user_name, test_user_id)
    
    if result:
        logger.info(f"✅ Workflow completed successfully. User ID: {result}")
    else:
        logger.error("❌ Workflow failed.")
    
    logger.info("Test finished for retrieve_and_store_portfolio_data.py.") 