import uuid
from typing import List, Dict, Any, Optional
import datetime

from backend.src.utils.database import get_cursor
from backend.src.utils.logging_config import init_logger

logger = init_logger(__name__)

TABLE_NAME = "public.user_portfolios"

def _create_user_portfolios_table_if_not_exists():
    """
    Create user_portfolios table in database if it doesn't exist.
    
    Creates table with schema for storing user portfolio positions including
    symbols, quantities, prices, and P&L data with composite primary key.
    
    Args:
        None
        
    Returns:
        None
        
    Raises:
        Exception: If table creation fails.
    """
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        user_id TEXT,
        email VARCHAR(255),
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

def store_portfolio_positions(user_id: str, email: str, positions_data: List[Dict[str, Any]]) -> Optional[str]:
    """
    Store portfolio position data in the user_portfolios table.
    
    Uses upsert logic to store or update positions. Uses the provided user_id.
    Handles conflicts based on composite primary key.
    
    Args:
        user_id: The user's ID.
        email: The user's email address.
        positions_data: List of dictionaries containing position data from IBKR.
        
    Returns:
        Optional[str]: The user_id used for storage, or None if operation failed.
    """
    _create_user_portfolios_table_if_not_exists()

    fetch_timestamp = datetime.datetime.now(datetime.timezone.utc)

    # Prepare the upsert SQL (INSERT ON CONFLICT UPDATE)
    upsert_sql = f"""
    INSERT INTO {TABLE_NAME} (
        user_id, email, fetch_timestamp, symbol, secType, currency,
        position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL,
        account
    ) VALUES (
        %(user_id)s, %(email)s, %(fetch_timestamp)s, %(symbol)s, %(secType)s, %(currency)s,
        %(position)s, %(marketPrice)s, %(marketValue)s, %(averageCost)s, %(unrealizedPNL)s, %(realizedPNL)s,
        %(account)s
    )
    ON CONFLICT (user_id, account, symbol, secType) 
    DO UPDATE SET
        email = EXCLUDED.email,
        fetch_timestamp = EXCLUDED.fetch_timestamp,
        currency = EXCLUDED.currency,
        position = EXCLUDED.position,
        marketPrice = EXCLUDED.marketPrice,
        marketValue = EXCLUDED.marketValue,
        averageCost = EXCLUDED.averageCost,
        unrealizedPNL = EXCLUDED.unrealizedPNL,
        realizedPNL = EXCLUDED.realizedPNL;
    """

    try:
        with get_cursor(dbname='user_data') as cursor:
            records_to_insert = []
            for pos in positions_data:
                record = {
                    "user_id": user_id,
                    "email": email,
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
                cursor.executemany(upsert_sql, records_to_insert)
                logger.info(f"Successfully stored/updated {len(records_to_insert)} positions for user_id: {user_id}.")
            else:
                logger.info(f"No positions data provided for user_id: '{user_id}'. Nothing stored.")
        return user_id
    except Exception as e:
        logger.error(f"🚨 Error storing portfolio positions for user_id '{user_id}': {e}", exc_info=True)
        return None

