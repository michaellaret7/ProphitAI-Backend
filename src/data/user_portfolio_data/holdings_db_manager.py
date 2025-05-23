import uuid
from typing import List, Dict, Any, Optional
import datetime

from src.utils.database import get_cursor
from src.utils.logging_config import init_logger

logger = init_logger(__name__)

TABLE_NAME = "public.user_portfolios"

def _create_user_portfolios_table_if_not_exists():
    """
    Creates the user_portfolios table in the database if it doesn't already exist.
    """
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        user_id TEXT,
        user_name TEXT,
        fetch_timestamp TIMESTAMP WITH TIME ZONE,
        symbol TEXT,
        secType TEXT,
        currency TEXT,
        position NUMERIC,
        marketPrice NUMERIC,
        marketValue NUMERIC,
        averageCost NUMERIC,
        unrealizedPNL NUMERIC,
        realizedPNL NUMERIC,
        account TEXT,
        PRIMARY KEY (user_id, account, symbol, secType)
    );
    """
    try:
        with get_cursor(dbname='user_data') as cursor:
            cursor.execute(create_table_sql)
        logger.info(f"Table {TABLE_NAME} ensured to exist with updated schema.")
    except Exception as e:
        logger.error(f"🚨 Error creating/updating table {TABLE_NAME}: {e}", exc_info=True)
        raise

def store_portfolio_positions(user_name: str, positions_data: List[Dict[str, Any]]) -> Optional[str]:
    """
    Stores the given portfolio positions data into the user_portfolios table.
    """
    _create_user_portfolios_table_if_not_exists()

    user_id = str(uuid.uuid4())
    fetch_timestamp = datetime.datetime.now(datetime.timezone.utc)

    insert_sql = f"""
    INSERT INTO {TABLE_NAME} (
        user_id, user_name, fetch_timestamp, symbol, secType, currency,
        position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL,
        account
    ) VALUES (
        %(user_id)s, %(user_name)s, %(fetch_timestamp)s, %(symbol)s, %(secType)s, %(currency)s,
        %(position)s, %(marketPrice)s, %(marketValue)s, %(averageCost)s, %(unrealizedPNL)s, %(realizedPNL)s,
        %(account)s
    );
    """

    try:
        with get_cursor(dbname='user_data') as cursor:
            records_to_insert = []
            for pos in positions_data:
                record = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "fetch_timestamp": fetch_timestamp,
                    "symbol": pos.get('symbol') or '',
                    "secType": pos.get('secType') or '',
                    "currency": pos.get('currency'),
                    "position": pos.get('position'),
                    "marketPrice": pos.get('marketPrice'),
                    "marketValue": pos.get('marketValue'),
                    "averageCost": pos.get('averageCost'),
                    "unrealizedPNL": pos.get('unrealizedPNL'),
                    "realizedPNL": pos.get('realizedPNL'),
                    "account": pos.get('account') or ''
                }
                records_to_insert.append(record)
            
            if records_to_insert:
                cursor.executemany(insert_sql, records_to_insert)
                logger.info(f"Successfully stored {len(records_to_insert)} positions for user_name: '{user_name}' with user_id: {user_id}.")
            else:
                logger.info(f"No positions data provided for user_name: '{user_name}'. Nothing stored.")
        return user_id
    except Exception as e:
        logger.error(f"🚨 Error storing portfolio positions for user_name '{user_name}': {e}", exc_info=True)
        return None

if __name__ == '__main__':
    from src.utils.logging_config import patch_print_for_logging
    from src.data.user_portfolio_data.fetch_ibkr_holdings import fetch_ibkr_portfolio_positions

    patch_print_for_logging()
    logger.info("🚀 Starting test for holdings_db_manager.py (with simplified schema)...")

    logger.info("Fetching portfolio positions from IBKR for testing...")
    test_positions = fetch_ibkr_portfolio_positions() # This will now fetch simplified data

    if test_positions is not None:
        logger.info(f"Fetched {len(test_positions)} positions (simplified)." )
        
        test_user_name = "test_user_beta"
        logger.info(f"Attempting to store positions for user_name: {test_user_name}...")
        generated_user_id = store_portfolio_positions(test_user_name, test_positions)

        if generated_user_id:
            logger.info(f"✅ Positions stored successfully under user_id: {generated_user_id}")
        else:
            logger.error(f"❌ Failed to store positions for user_name: {test_user_name}")
    else:
        logger.warning("⚠️ No positions fetched from IBKR. Cannot test storage.")

    from src.utils.ib_utils import get_ib
    ib_instance = get_ib()
    if ib_instance and ib_instance.isConnected():
        logger.info("Ensuring IBKR disconnection for script after test.")
        ib_instance.disconnect()

    logger.info("Test finished for holdings_db_manager.py.") 