#!/usr/bin/env python3
"""
Comprehensive timezone fix script that:
1. Scans all actively trading tickers for UTC/EST mismatches
2. Logs problematic tickers to tz_fix.csv
3. Fixes timezone issues using fix_timezone_final logic
4. Recovers missing data using recover_data logic

Usage: python fix_all_timezones.py [--scan-only] [--dry-run]
"""

import sys
import csv
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

sys.path.append('/Users/michaellaret/Desktop/ProphitAI')

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, Price
from app.utils.decorators.database import with_session, with_transaction
from sqlalchemy import extract, func, text
from sqlalchemy.orm import Session

# Import data recovery functionality
from app.db.jobs.price_table import UpdatePriceTable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CSV_FILE = 'tz_fix.csv'


# =============================================================================
# TIMEZONE FIX FUNCTIONS
# =============================================================================

@with_session('market')
def find_transition_date(ticker_symbol: str, session: Session = None) -> Optional[date]:
    """Find last 9:30 AM timestamp (last day of EST data)."""
    ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()
    if not ticker:
        return None

    last_930 = session.query(Price).filter(
        Price.ticker_id == ticker.id,
        extract('hour', Price.datetime) == 9,
        extract('minute', Price.datetime) == 30
    ).order_by(Price.datetime.desc()).first()

    if last_930:
        return last_930.datetime.date() + timedelta(days=1)
    return None


@with_transaction('market')
def fix_timezone_final(
    ticker_symbol: str,
    transition_date: Optional[date] = None,
    dry_run: bool = False,
    session: Session = None
) -> Dict:
    """
    Fix timezone using temp table to avoid primary key conflicts.
    """
    ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()
    if not ticker:
        return {'status': 'ERROR', 'message': 'Ticker not found'}

    if not transition_date:
        transition_date = find_transition_date(ticker_symbol)
        if not transition_date:
            return {'status': 'ERROR', 'message': 'Could not find transition date'}

    logger.info(f"Transition date: {transition_date}")
    ticker_id = str(ticker.id)
    transition_dt = datetime.combine(transition_date, datetime.min.time())

    # Count what we'll process
    est_count = session.query(Price).filter(
        Price.ticker_id == ticker.id,
        Price.datetime < transition_dt
    ).count()

    utc_dup_count = session.query(Price).filter(
        Price.ticker_id == ticker.id,
        Price.datetime >= transition_dt
    ).count()

    logger.info(f"EST records to convert: {est_count}")
    logger.info(f"UTC duplicates to delete: {utc_dup_count}")

    if dry_run:
        return {
            'status': 'DRY_RUN',
            'est_to_convert': est_count,
            'utc_to_delete': utc_dup_count,
            'transition_date': transition_date.isoformat()
        }

    # Step 1: Delete UTC duplicates (>= transition date)
    logger.info("Step 1: Deleting UTC duplicates...")
    deleted_utc = session.query(Price).filter(
        Price.ticker_id == ticker.id,
        Price.datetime >= transition_dt
    ).delete(synchronize_session=False)
    logger.info(f"  Deleted {deleted_utc} UTC duplicate records")
    session.flush()

    # Step 2: Create temp table and copy EST data with converted times
    logger.info("Step 2: Creating temp table with converted UTC times...")

    create_temp = text("""
        CREATE TEMP TABLE prices_temp AS
        SELECT
            ticker_id,
            (datetime AT TIME ZONE 'America/New_York') AT TIME ZONE 'UTC' as datetime,
            open,
            high,
            low,
            close,
            volume
        FROM price_data.prices
        WHERE ticker_id = :ticker_id
        AND datetime < :transition_date
    """)

    session.execute(create_temp, {
        'ticker_id': ticker_id,
        'transition_date': transition_dt
    })
    logger.info("  Temp table created with converted times")
    session.flush()

    # Step 3: Delete original EST records
    logger.info("Step 3: Deleting original EST records...")
    deleted_est = session.query(Price).filter(
        Price.ticker_id == ticker.id,
        Price.datetime < transition_dt
    ).delete(synchronize_session=False)
    logger.info(f"  Deleted {deleted_est} EST records")
    session.flush()

    # Step 4: Insert converted records from temp table
    logger.info("Step 4: Inserting converted UTC records...")

    insert_converted = text("""
        INSERT INTO price_data.prices (ticker_id, datetime, open, high, low, close, volume)
        SELECT ticker_id, datetime, open, high, low, close, volume
        FROM prices_temp
    """)

    result = session.execute(insert_converted)
    inserted = result.rowcount
    logger.info(f"  Inserted {inserted} converted records")

    # Step 5: Drop temp table
    session.execute(text("DROP TABLE prices_temp"))

    session.commit()
    logger.info("✅ Complete!")

    return {
        'status': 'SUCCESS',
        'ticker': ticker_symbol,
        'transition_date': transition_date.isoformat(),
        'utc_duplicates_deleted': deleted_utc,
        'est_records_deleted': deleted_est,
        'utc_records_inserted': inserted
    }


@with_session('market')
def verify_fix(ticker_symbol: str, session: Session = None) -> Dict:
    """Verify the fix worked."""
    ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()
    if not ticker:
        return {}

    total = session.query(func.count(Price.datetime)).filter(
        Price.ticker_id == ticker.id
    ).scalar()

    count_930 = session.query(func.count(Price.datetime)).filter(
        Price.ticker_id == ticker.id,
        extract('hour', Price.datetime) == 9,
        extract('minute', Price.datetime) == 30
    ).scalar()

    count_1330 = session.query(func.count(Price.datetime)).filter(
        Price.ticker_id == ticker.id,
        extract('hour', Price.datetime) == 13,
        extract('minute', Price.datetime) == 30
    ).scalar()

    count_1730 = session.query(func.count(Price.datetime)).filter(
        Price.ticker_id == ticker.id,
        extract('hour', Price.datetime) == 17,
        extract('minute', Price.datetime) == 30
    ).scalar()

    return {
        'total': total,
        '9:30 (EST)': count_930,
        '13:30 (UTC market open)': count_1330,
        '17:30 (UTC ~1:30PM EST)': count_1730
    }


# =============================================================================
# TIMEZONE DETECTION AND PROCESSING
# =============================================================================

@with_session('market')
def detect_timezone_mismatches(session=None) -> List[Dict]:
    """
    Scan all actively trading tickers for UTC/EST timezone mismatches.

    Returns:
        List of dicts with ticker info and mismatch details
    """
    logger.info("Scanning for timezone mismatches in actively trading tickers...")

    # Get all actively trading tickers
    tickers = session.query(Ticker).filter(
        Ticker.is_actively_trading == True
    ).all()

    logger.info(f"Found {len(tickers)} actively trading tickers to scan")

    mismatched_tickers = []

    for idx, ticker in enumerate(tickers, 1):
        if idx % 100 == 0:
            logger.info(f"Progress: {idx}/{len(tickers)} tickers scanned")

        # Check for 9:30 AM timestamps (EST data)
        count_930 = session.query(func.count(Price.datetime)).filter(
            Price.ticker_id == ticker.id,
            extract('hour', Price.datetime) == 9,
            extract('minute', Price.datetime) == 30
        ).scalar()

        # Check for 13:30 timestamps (UTC market open)
        count_1330 = session.query(func.count(Price.datetime)).filter(
            Price.ticker_id == ticker.id,
            extract('hour', Price.datetime) == 13,
            extract('minute', Price.datetime) == 30
        ).scalar()

        # Get total price records
        total_records = session.query(func.count(Price.datetime)).filter(
            Price.ticker_id == ticker.id
        ).scalar()

        # If we have 9:30 timestamps, this ticker has EST data
        if count_930 > 0:
            # Find transition date
            transition_date = find_transition_date(ticker.ticker)

            mismatched_tickers.append({
                'ticker': ticker.ticker,
                'ticker_id': str(ticker.id),
                'est_records_930': count_930,
                'utc_records_1330': count_1330,
                'total_records': total_records,
                'transition_date': transition_date.isoformat() if transition_date else 'Unknown',
                'sector': ticker.sector or 'N/A',
                'industry': ticker.industry or 'N/A'
            })

            logger.info(f"  ⚠️  {ticker.ticker}: {count_930} EST records found")

    logger.info(f"\n✅ Scan complete: {len(mismatched_tickers)} tickers with timezone issues")
    return mismatched_tickers


def write_to_csv(mismatched_tickers: List[Dict]) -> None:
    """Write mismatched tickers to CSV file."""
    logger.info(f"Writing {len(mismatched_tickers)} tickers to {CSV_FILE}...")

    with open(CSV_FILE, 'w', newline='') as csvfile:
        if mismatched_tickers:
            fieldnames = mismatched_tickers[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(mismatched_tickers)

    logger.info(f"✅ Written to {CSV_FILE}")


def read_from_csv() -> List[str]:
    """Read ticker symbols from CSV file."""
    try:
        tickers = []
        with open(CSV_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tickers.append(row['ticker'])
        logger.info(f"Read {len(tickers)} tickers from {CSV_FILE}")
        return tickers
    except FileNotFoundError:
        logger.error(f"CSV file {CSV_FILE} not found. Run with --scan-only first.")
        return []


def fix_and_recover_ticker(ticker_symbol: str, dry_run: bool = False) -> Dict:
    """
    Fix timezone issues and recover data for a single ticker.

    Args:
        ticker_symbol: Ticker symbol to fix
        dry_run: If True, only simulate the fix

    Returns:
        Dict with results from fix and recovery
    """
    logger.info("=" * 80)
    logger.info(f"PROCESSING: {ticker_symbol}")
    logger.info("=" * 80)

    # Initialize UpdatePriceTable for data recovery
    updater = UpdatePriceTable()

    results = {
        'ticker': ticker_symbol,
        'fix_status': None,
        'recovery_status': None
    }

    # Step 1: Fix timezone
    logger.info(f"\n[1/3] Fixing timezone for {ticker_symbol}...")
    try:
        fix_result = fix_timezone_final(ticker_symbol, dry_run=dry_run)
        results['fix_status'] = fix_result.get('status')
        results['fix_details'] = fix_result

        if fix_result['status'] == 'SUCCESS':
            logger.info(f"✅ Timezone fix successful")
            logger.info(f"   UTC duplicates deleted: {fix_result.get('utc_duplicates_deleted', 0)}")
            logger.info(f"   UTC records inserted: {fix_result.get('utc_records_inserted', 0)}")
        elif fix_result['status'] == 'DRY_RUN':
            logger.info(f"🔍 Dry run - would process {fix_result.get('est_to_convert', 0)} EST records")
            return results  # Don't proceed with recovery in dry run
        else:
            logger.warning(f"⚠️  Fix failed: {fix_result.get('message')}")
            return results

    except Exception as e:
        logger.error(f"❌ Error fixing timezone: {str(e)}")
        results['fix_status'] = 'ERROR'
        results['fix_error'] = str(e)
        return results

    # Step 2: Verify fix
    logger.info(f"\n[2/3] Verifying timezone fix for {ticker_symbol}...")
    try:
        verify_result = verify_fix(ticker_symbol)
        results['verify_details'] = verify_result

        if verify_result.get('9:30 (EST)', 0) == 0:
            logger.info(f"✅ Verification passed - no EST timestamps remaining")
        else:
            logger.warning(f"⚠️  Verification warning - {verify_result.get('9:30 (EST)', 0)} EST timestamps still present")

    except Exception as e:
        logger.warning(f"⚠️  Verification error: {str(e)}")

    # Step 3: Recover data
    logger.info(f"\n[3/3] Recovering missing data for {ticker_symbol}...")
    try:
        records_inserted = updater.recover_ticker_data(ticker_symbol)

        if records_inserted > 0:
            results['recovery_status'] = 'SUCCESS'
            results['records_recovered'] = records_inserted
            logger.info(f"✅ Recovery successful - {records_inserted} records inserted")
        elif records_inserted == 0:
            results['recovery_status'] = 'NO_NEW_DATA'
            results['records_recovered'] = 0
            logger.info(f"ℹ️  No new data to recover")
        else:
            results['recovery_status'] = 'ERROR'
            logger.warning(f"⚠️  Recovery failed")

    except Exception as e:
        logger.error(f"❌ Error recovering data: {str(e)}")
        results['recovery_status'] = 'ERROR'
        results['recovery_error'] = str(e)

    logger.info("=" * 80)
    return results


def process_all_tickers(dry_run: bool = False) -> None:
    """
    Read tickers from CSV and process each one.

    Args:
        dry_run: If True, only simulate fixes
    """
    tickers = read_from_csv()

    if not tickers:
        logger.error("No tickers to process")
        return

    logger.info(f"\n{'DRY RUN - ' if dry_run else ''}Processing {len(tickers)} tickers...")
    logger.info("=" * 80)

    all_results = []

    for idx, ticker in enumerate(tickers, 1):
        logger.info(f"\n\nTICKER {idx}/{len(tickers)}")
        result = fix_and_recover_ticker(ticker, dry_run=dry_run)
        all_results.append(result)

    # Summary
    logger.info("\n\n" + "=" * 80)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 80)

    successful_fixes = sum(1 for r in all_results if r.get('fix_status') == 'SUCCESS')
    successful_recoveries = sum(1 for r in all_results if r.get('recovery_status') == 'SUCCESS')
    total_recovered = sum(r.get('records_recovered', 0) for r in all_results)

    logger.info(f"Total tickers processed: {len(all_results)}")
    logger.info(f"Successful timezone fixes: {successful_fixes}")
    logger.info(f"Successful data recoveries: {successful_recoveries}")
    logger.info(f"Total records recovered: {total_recovered}")
    logger.info("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Comprehensive timezone fix and data recovery script'
    )
    parser.add_argument(
        '--scan-only',
        action='store_true',
        help='Only scan for mismatches and write to CSV, do not fix'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate fixes without making changes'
    )
    parser.add_argument(
        '--ticker',
        type=str,
        help='Process a single ticker instead of all tickers in CSV'
    )

    args = parser.parse_args()

    try:
        if args.scan_only:
            # Scan for mismatches and write to CSV
            mismatched = detect_timezone_mismatches()
            write_to_csv(mismatched)

        elif args.ticker:
            # Process single ticker
            logger.info(f"Processing single ticker: {args.ticker}")
            result = fix_and_recover_ticker(args.ticker.upper(), dry_run=args.dry_run)

            logger.info("\n" + "=" * 80)
            logger.info("RESULT")
            logger.info("=" * 80)
            for key, value in result.items():
                logger.info(f"{key}: {value}")

        else:
            # Process all tickers from CSV
            process_all_tickers(dry_run=args.dry_run)

        logger.info("\n✅ Script completed successfully")

    except Exception as e:
        logger.error(f"\n❌ Script failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()