import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.core.db_config import MacroDataSession
from app.db.core.models.macro_data_models import CommodityPrices
from app.utils.time_utils import get_current_utc_time

load_dotenv()

def get_commodity_data(symbol, from_date=None, to_date=None, interval='1day'):
    """
    Get OHLC data for a specific commodity.
    
    Args:
        symbol: Commodity symbol (e.g., 'GCUSD', 'CLUSD')
        from_date: Start date in YYYY-MM-DD format (optional)
        to_date: End date in YYYY-MM-DD format (optional)
        interval: Data interval - '1min', '5min', '15min', '30min', '1hour', '4hour', '1day' (default: '1day')
    
    Returns:
        DataFrame with OHLC data
    """
    
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("Set FMP_API_KEY environment variable")
    
    base_url = "https://financialmodelingprep.com/api/v3"
    
    print(f"Fetching {symbol} at {interval} interval...")
    
    # Use different endpoint for intraday vs daily data
    if interval == '1day':
        hist_url = f"{base_url}/historical-price-full/{symbol}?apikey={api_key}"
    else:
        hist_url = f"{base_url}/historical-chart/{interval}/{symbol}?apikey={api_key}"
    
    if from_date:
        hist_url += f"&from={from_date}"
    if to_date:
        hist_url += f"&to={to_date}"
    
    response = requests.get(hist_url)
    data = response.json()
    
    # Handle different response structures
    if interval == '1day':
        if 'historical' not in data or not data['historical']:
            print(f"No data found for {symbol}")
            return pd.DataFrame()
        df = pd.DataFrame(data['historical'])
    else:
        if not data or not isinstance(data, list):
            print(f"No data found for {symbol}")
            return pd.DataFrame()
        df = pd.DataFrame(data)
    
    df['symbol'] = symbol

    # Convert date strings to date objects for database insertion
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date

    return df


def push_commodity_data_to_db(symbol: str, df: pd.DataFrame) -> int:
    """
    Push commodity OHLCV data to the database.

    Uses upsert logic - updates existing records and inserts new ones
    based on unique constraint (symbol, date).

    Args:
        symbol: Commodity symbol
        df: DataFrame with columns [date, open, high, low, close, volume]

    Returns:
        Number of records inserted/updated
    """
    if df.empty:
        print(f"No data to insert for {symbol}")
        return 0

    session = MacroDataSession()
    try:
        current_time = get_current_utc_time()

        # Prepare records for insertion
        records = []
        for _, row in df.iterrows():
            records.append({
                'symbol': symbol,
                'date': row['date'],
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'volume': float(row['volume']) if pd.notna(row['volume']) else None,
                'created_at': current_time,
                'updated_at': current_time
            })

        # Use PostgreSQL INSERT ... ON CONFLICT for upsert
        stmt = insert(CommodityPrices).values(records)

        # On conflict, update all fields except id and created_at
        stmt = stmt.on_conflict_do_update(
            constraint='uq_commodity_symbol_date',
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
                'updated_at': current_time
            }
        )

        session.execute(stmt)
        session.commit()

        print(f"✓ Inserted/updated {len(records)} records for {symbol}")
        return len(records)

    except Exception as e:
        session.rollback()
        print(f"✗ Error inserting data for {symbol}: {e}")
        raise
    finally:
        session.close()


def fetch_and_store_commodity_data(symbol: str, from_date=None, to_date=None, interval='1day') -> int:
    """
    Fetch commodity data from FMP API and store in database.

    Args:
        symbol: Commodity symbol (e.g., 'GCUSD', 'CLUSD')
        from_date: Start date in YYYY-MM-DD format (optional)
        to_date: End date in YYYY-MM-DD format (optional)
        interval: Data interval (default: '1day')

    Returns:
        Number of records inserted/updated

    Example:
        >>> count = fetch_and_store_commodity_data('GCUSD', '2024-01-01', '2024-12-31')
        >>> print(f"Loaded {count} records")
    """
    # Fetch data from API
    df = get_commodity_data(symbol, from_date, to_date, interval)

    if df.empty:
        return 0

    # Push to database
    count = push_commodity_data_to_db(symbol, df)

    return count




if __name__ == "__main__":
    # Example: Get gold data for 2024
    # df = get_commodity_data("LBUSD", from_date="2025-01-01", to_date="2024-12-31")
    commodity_tickers = [
        "ZQUSD",  # 30-Day Fed Funds Futures
        "ALIUSD",  # Aluminum
        "ZMUSD",  # Soybean Meal
        "GCUSD",  # Gold
        "ZLUSX",  # Soybean Oil
        "KEUSX",  # Kansas City Wheat (Hard Red Winter Wheat)
        "SILUSD",  # Physical Silver Index (similar to SI)
        "ZCUSX",  # Corn
        "HEUSX",  # Lean Hogs
        "PLUSD",  # Platinum
        "HGUSD",  # Copper
        "SBUSX",  # Sugar #11
        "SIUSD",  # Silver
        "CTUSX",  # Cotton #2
        "DXUSD",  # U.S. Dollar Index (DXY)
        "ZSUSX",  # Soybeans
        "LBUSD",  # Lumber
        "LEUSX",  # Live Cattle
        "NGUSD",  # Natural Gas
        "CLUSD",  # Crude Oil (WTI)
        "OJUSX",  # Orange Juice
        "KCUSX",  # Coffee (Arabica)
        "PAUSD",  # Palladium
        "GFUSX",  # Feeder Cattle
        "CCUSD",  # Cocoa
        "ZNUSD",  # U.S. 10-Year Treasury Note Futures
        "BZUSD",  # Brent Crude Oil
        "YMUSD",  # Dow Jones (Mini) Index
        "RBUSD",  # RBOB Gasoline
        "HOUSD",  # Heating Oil
    ]
    # Example: Fetch and store all commodity data
    for ticker in commodity_tickers:
        try:
            count = fetch_and_store_commodity_data(
                ticker,
                from_date="1990-01-01",
                to_date="2025-11-07"
            )
            print(f"{ticker}: {count} records loaded")
        except Exception as e:
            print(f"Failed to load {ticker}: {e}")
    

"""
commodity_tickers = [
    "ZQUSD",  # 30-Day Fed Funds Futures
    "ALIUSD",  # Aluminum
    "ZBUSD",  # U.S. 30-Year Treasury Bond Futures
    "ZMUSD",  # Soybean Meal
    "GCUSD",  # Gold
    "ZLUSX",  # Soybean Oil
    "KEUSX",  # Kansas City Wheat (Hard Red Winter Wheat)
    "ZFUSD",  # U.S. 5-Year Treasury Note Futures
    "SILUSD",  # Physical Silver Index (similar to SI)
    "ZCUSX",  # Corn
    "HEUSX",  # Lean Hogs
    "PLUSD",  # Platinum
    "HGUSD",  # Copper
    "SBUSX",  # Sugar #11
    "SIUSD",  # Silver
    "CTUSX",  # Cotton #2
    "DXUSD",  # U.S. Dollar Index (DXY)
    "ZSUSX",  # Soybeans
    "LBUSD",  # Lumber
    "LEUSX",  # Live Cattle
    "NGUSD",  # Natural Gas
    "CLUSD",  # Crude Oil (WTI)
    "OJUSX",  # Orange Juice
    "KCUSX",  # Coffee (Arabica)
    "PAUSD",  # Palladium
    "GFUSX",  # Feeder Cattle
    "ZTUSD",  # U.S. 2-Year Treasury Note Futures
    "CCUSD",  # Cocoa
    "NQUSD",  # Nasdaq 100 E-mini Index
    "ZNUSD",  # U.S. 10-Year Treasury Note Futures
    "RTYUSD",  # Russell 2000 Index Futures
    "BZUSD",  # Brent Crude Oil
    "YMUSD",  # Dow Jones (Mini) Index
    "RBUSD",  # RBOB Gasoline
    "HOUSD",  # Heating Oil
]
"""