import uuid
from typing import List, Dict, Any, Optional
import datetime

from backend.src.utils.database import get_cursor
from backend.src.utils.logging_config import init_logger

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

def store_portfolio_positions(user_name: str, positions_data: List[Dict[str, Any]], user_id: Optional[str] = None) -> Optional[str]:
    """
    Stores the given portfolio positions data into the user_portfolios table.
    If user_id is provided, it will use that ID.
    If user_id is not provided, it will check if a portfolio exists for the user_name.
    If it exists, it will update the existing records. If not, it will create new records.
    """
    _create_user_portfolios_table_if_not_exists()

    fetch_timestamp = datetime.datetime.now(datetime.timezone.utc)

    # If user_id is not provided, check if user exists
    if user_id is None:
        with get_cursor(dbname='user_data') as cursor:
            # Check if user already has a portfolio
            cursor.execute(f"SELECT DISTINCT user_id FROM {TABLE_NAME} WHERE user_name = %s LIMIT 1", (user_name,))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
                logger.info(f"Found existing portfolio for user_name: '{user_name}' with user_id: {user_id}")
            else:
                user_id = str(uuid.uuid4())
                logger.info(f"Creating new portfolio for user_name: '{user_name}' with user_id: {user_id}")

    # Prepare the upsert SQL (INSERT ON CONFLICT UPDATE)
    upsert_sql = f"""
    INSERT INTO {TABLE_NAME} (
        user_id, user_name, fetch_timestamp, symbol, secType, currency,
        position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL,
        account
    ) VALUES (
        %(user_id)s, %(user_name)s, %(fetch_timestamp)s, %(symbol)s, %(secType)s, %(currency)s,
        %(position)s, %(marketPrice)s, %(marketValue)s, %(averageCost)s, %(unrealizedPNL)s, %(realizedPNL)s,
        %(account)s
    )
    ON CONFLICT (user_id, account, symbol, secType) 
    DO UPDATE SET
        user_name = EXCLUDED.user_name,
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
                cursor.executemany(upsert_sql, records_to_insert)
                logger.info(f"Successfully stored/updated {len(records_to_insert)} positions for user_name: '{user_name}' with user_id: {user_id}.")
            else:
                logger.info(f"No positions data provided for user_name: '{user_name}'. Nothing stored.")
        return user_id
    except Exception as e:
        logger.error(f"🚨 Error storing portfolio positions for user_name '{user_name}': {e}", exc_info=True)
        return None

