"""EOD Close Price Backfill Script.

This script inserts EOD (End of Day) close price rows at 21:00 UTC
for each trading day based on FMP's daily historical price data.

Usage:
    # Test on a single ticker first:
    from script import backfill_single_ticker
    backfill_single_ticker('AAPL')

    # Run on all tickers from CSV:
    from script import backfill_all_tickers
    backfill_all_tickers()
"""

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Price, Ticker
from app.utils.decorators.database import with_session, with_transaction
from datetime import datetime, time
from typing import Tuple, Optional, List
from app.db.core.pull_fmp_data import FMP_API_DATA
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time as time_module
import pandas as pd

# Path to the CSV file containing active tickers
CSV_PATH = Path(__file__).parent / 'tickers.csv'

# EOD time in UTC (21:00 = 4PM EST market close)
EOD_HOUR_UTC = 21
EOD_MINUTE_UTC = 0


def load_tickers_from_csv() -> List[str]:
    """Load ticker symbols from the CSV file."""
    with open(CSV_PATH, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers


@with_session('market')
def get_eod_rows_for_ticker(ticker: str, limit: int = 100, session=None) -> List[dict]:
    """Get all Price rows at 21:00 UTC for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        limit: Max rows to return (default 100, use None for all)

    Returns:
        List of dicts with datetime, open, high, low, close, volume
    """
    from sqlalchemy import extract

    ticker = ticker.upper()

    query = session.query(Price).join(Ticker).filter(
        Ticker.ticker == ticker,
        extract('hour', Price.datetime) == 21,
        extract('minute', Price.datetime) == 0
    ).order_by(Price.datetime.desc())

    if limit:
        query = query.limit(limit)

    rows = query.all()

    return [
        {
            'datetime': row.datetime,
            'open': row.open,
            'high': row.high,
            'low': row.low,
            'close': row.close,
            'volume': row.volume
        }
        for row in rows
    ]


@with_session('market')
def get_ticker_id(ticker: str, session=None) -> Optional[str]:
    """Get the ticker_id (UUID) for a ticker symbol."""
    ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()
    if ticker_obj:
        return str(ticker_obj.id)
    return None


@with_session('market')
def get_ticker_timestamp_range(ticker: str, session=None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Get the first and last timestamps for a ticker in the database.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Tuple of (first_timestamp, last_timestamp) or (None, None) if no data exists
    """
    ticker = ticker.upper()

    result = session.query(
        func.min(Price.datetime).label('first'),
        func.max(Price.datetime).label('last')
    ).join(Ticker).filter(
        Ticker.ticker == ticker
    ).first()

    if result and result.first and result.last:
        return result.first, result.last

    return None, None


def get_fmp_eod_data(ticker: str, from_date: datetime, to_date: datetime) -> Optional[dict]:
    """Fetch EOD price data from FMP API."""
    fmp = FMP_API_DATA()
    data = fmp.get_daily_prices_for_ticker(ticker, from_date, to_date)
    return data


def build_eod_price_records(ticker_id: str, fmp_data: dict) -> List[dict]:
    """Convert FMP daily data to Price records with 21:00 UTC timestamps.

    Args:
        ticker_id: The UUID of the ticker
        fmp_data: FMP API response containing 'historical' key with daily OHLCV data

    Returns:
        List of price record dicts ready for bulk insert
    """
    if not fmp_data or 'historical' not in fmp_data:
        return []

    # Max value for PostgreSQL Integer (32-bit signed)
    MAX_INT32 = 2147483647

    records = []
    for day_data in fmp_data['historical']:
        # FMP returns date as 'YYYY-MM-DD' string
        date_str = day_data.get('date')
        if not date_str:
            continue

        # Parse date and set time to 21:00 UTC (4PM EST market close)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        eod_datetime = datetime.combine(date_obj.date(), time(EOD_HOUR_UTC, EOD_MINUTE_UTC))

        # Cap volume to max int32 to avoid PostgreSQL integer overflow
        volume = day_data.get('volume')
        if volume is not None and volume > MAX_INT32:
            volume = MAX_INT32

        records.append({
            'ticker_id': ticker_id,
            'datetime': eod_datetime,
            'open': day_data.get('open'),
            'high': day_data.get('high'),
            'low': day_data.get('low'),
            'close': day_data.get('close'),
            'volume': volume
        })

    return records


def insert_eod_prices(ticker_id: str, records: List[dict], batch_size: int = 500) -> int:
    """Bulk upsert EOD price records in batches, overwriting existing 21:00 rows.

    Args:
        ticker_id: The ticker UUID (not used directly, already in records)
        records: List of price record dicts
        batch_size: Number of records per batch (default 500)

    Returns:
        Total number of records inserted/updated
    """
    if not records:
        return 0

    session = MarketSession()
    total_affected = 0

    try:
        # Process in batches to avoid query size limits
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            stmt = insert(Price).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id', 'datetime'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume
                }
            )
            result = session.execute(stmt)
            total_affected += result.rowcount

        session.commit()
        return total_affected
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def backfill_single_ticker(ticker: str) -> dict:
    """Backfill EOD prices for a single ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Dict with status and details of the operation
    """
    ticker = ticker.upper()
    result = {
        'ticker': ticker,
        'status': 'unknown',
        'records_inserted': 0,
        'message': ''
    }

    print(f"\n{'='*60}")
    print(f"Processing: {ticker}")
    print('='*60)

    # Step 1: Get ticker_id
    ticker_id = get_ticker_id(ticker)
    if not ticker_id:
        result['status'] = 'error'
        result['message'] = f"Ticker '{ticker}' not found in database"
        print(f"  ERROR: {result['message']}")
        return result
    print(f"  Ticker ID: {ticker_id}")

    # Step 2: Get date range
    first_date, last_date = get_ticker_timestamp_range(ticker)
    if not first_date or not last_date:
        result['status'] = 'error'
        result['message'] = f"No existing price data found for {ticker}"
        print(f"  ERROR: {result['message']}")
        return result
    print(f"  Date range: {first_date.date()} to {last_date.date()}")

    # Step 3: Fetch EOD data from FMP
    print(f"  Fetching EOD data from FMP...")
    fmp_data = get_fmp_eod_data(ticker, first_date, last_date)

    if not fmp_data or 'historical' not in fmp_data:
        result['status'] = 'error'
        result['message'] = f"No EOD data returned from FMP for {ticker}"
        print(f"  ERROR: {result['message']}")
        return result

    num_days = len(fmp_data.get('historical', []))
    print(f"  FMP returned {num_days} days of EOD data")

    # Step 4: Build price records
    records = build_eod_price_records(ticker_id, fmp_data)
    print(f"  Built {len(records)} EOD price records")

    # Step 5: Insert records
    try:
        inserted = insert_eod_prices(ticker_id, records)
        result['status'] = 'success'
        result['records_inserted'] = inserted
        result['message'] = f"Upserted {len(records)} EOD records ({inserted} rows affected)"
        print(f"  SUCCESS: {result['message']}")
    except Exception as e:
        result['status'] = 'error'
        result['message'] = f"Database error: {str(e)}"
        print(f"  ERROR: {result['message']}")

    return result


def backfill_all_tickers(max_workers: int = 10) -> dict:
    """Backfill EOD prices for all tickers in the CSV file using thread pooling.

    Args:
        max_workers: Number of concurrent threads (default 10)

    Returns:
        Summary dict with counts and any errors
    """
    tickers = load_tickers_from_csv()
    total = len(tickers)

    print(f"\n{'='*60}")
    print(f"EOD BACKFILL - Processing {total} tickers with {max_workers} threads")
    print('='*60)

    # Thread-safe counters
    lock = threading.Lock()
    summary = {
        'total': total,
        'success': 0,
        'errors': 0,
        'total_records_inserted': 0,
        'failed_tickers': [],
        'processed': 0
    }

    def process_ticker(ticker: str) -> dict:
        """Process a single ticker (runs in thread)."""
        result = backfill_single_ticker(ticker)

        with lock:
            summary['processed'] += 1
            if result['status'] == 'success':
                summary['success'] += 1
                summary['total_records_inserted'] += result['records_inserted']
            else:
                summary['errors'] += 1
                summary['failed_tickers'].append({'ticker': ticker, 'error': result['message']})

            # Progress update every 25 tickers
            if summary['processed'] % 25 == 0:
                print(f"\n>>> Progress: {summary['processed']}/{total} tickers processed")

        return result

    start_time = time_module.time()

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_ticker, ticker): ticker for ticker in tickers}

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                future.result()
            except Exception as e:
                with lock:
                    summary['errors'] += 1
                    summary['failed_tickers'].append({'ticker': ticker, 'error': str(e)})

    elapsed_time = time_module.time() - start_time

    # Print summary
    print(f"\n\n{'='*60}")
    print("BACKFILL COMPLETE - SUMMARY")
    print('='*60)
    print(f"Total tickers processed: {summary['total']}")
    print(f"Successful: {summary['success']}")
    print(f"Errors: {summary['errors']}")
    print(f"Total EOD records upserted: {summary['total_records_inserted']}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    print(f"Average time per ticker: {elapsed_time/total:.2f} seconds")

    if summary['failed_tickers']:
        print(f"\nFailed tickers:")
        for item in summary['failed_tickers']:
            print(f"  - {item['ticker']}: {item['error']}")

    return summary





