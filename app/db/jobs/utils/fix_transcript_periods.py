#!/usr/bin/env python3
"""
Fix earnings transcript period formatting inconsistencies.

Scans all actively traded tickers and fixes period format issues:
- Deletes duplicates where both '1' and 'Q1' format exist (keeps 'Q1')
- Updates standalone integer format ('1', '2', '3', '4') to 'Q' format ('Q1', 'Q2', etc.)

Usage: python -m app.db.jobs.utils.fix_transcript_periods [--dry-run] [--workers N]
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy import and_

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, EarningsTranscript

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Integer format periods that need fixing
INTEGER_PERIODS = ('1', '2', '3', '4')


@dataclass
class TickerResult:
    """Result of processing a single ticker."""
    ticker: str
    deleted: int
    updated: int
    error: Optional[str] = None


def get_actively_traded_tickers() -> List[Tuple[str, str]]:
    """
    Get all actively traded non-ETF tickers.

    Returns:
        List of (ticker_id, ticker_symbol) tuples
    """
    with MarketSession() as session:
        tickers = session.query(Ticker.id, Ticker.ticker).filter(
            and_(
                Ticker.is_actively_trading == True,
                Ticker.is_etf == False
            )
        ).all()
        return [(str(t.id), t.ticker) for t in tickers]


def process_ticker(ticker_id: str, ticker_symbol: str, dry_run: bool = False) -> TickerResult:
    """
    Process a single ticker's earnings transcripts.

    For each transcript with integer period format:
    - If duplicate exists with 'Q' format -> DELETE the integer format
    - If no duplicate -> UPDATE to 'Q' format

    Args:
        ticker_id: UUID of the ticker
        ticker_symbol: Ticker symbol for logging
        dry_run: If True, don't make changes

    Returns:
        TickerResult with counts of deleted and updated records
    """
    deleted = 0
    updated = 0

    try:
        with MarketSession() as session:
            # Get all transcripts with integer format periods for this ticker
            integer_transcripts = session.query(EarningsTranscript).filter(
                and_(
                    EarningsTranscript.ticker_id == ticker_id,
                    EarningsTranscript.period.in_(INTEGER_PERIODS)
                )
            ).all()

            if not integer_transcripts:
                return TickerResult(ticker=ticker_symbol, deleted=0, updated=0)

            for transcript in integer_transcripts:
                quarter_num = transcript.period  # '1', '2', '3', or '4'
                q_format = f'Q{quarter_num}'     # 'Q1', 'Q2', 'Q3', or 'Q4'

                # Check if 'Q' format duplicate exists
                duplicate = session.query(EarningsTranscript).filter(
                    and_(
                        EarningsTranscript.ticker_id == ticker_id,
                        EarningsTranscript.year == transcript.year,
                        EarningsTranscript.period == q_format
                    )
                ).first()

                if duplicate:
                    # Duplicate exists - delete the integer format record
                    if not dry_run:
                        session.delete(transcript)
                    deleted += 1
                else:
                    # No duplicate - update the period to 'Q' format
                    if not dry_run:
                        transcript.period = q_format
                    updated += 1

            if not dry_run:
                session.commit()

        return TickerResult(ticker=ticker_symbol, deleted=deleted, updated=updated)

    except Exception as e:
        logger.error(f"Error processing {ticker_symbol}: {str(e)}")
        return TickerResult(ticker=ticker_symbol, deleted=0, updated=0, error=str(e))


def fix_all_transcript_periods(dry_run: bool = False, max_workers: int = 10) -> None:
    """
    Fix period formatting for all actively traded tickers using thread pool.

    Args:
        dry_run: If True, only simulate changes
        max_workers: Number of parallel workers
    """
    logger.info("=" * 80)
    logger.info(f"{'DRY RUN - ' if dry_run else ''}Fixing Earnings Transcript Period Formatting")
    logger.info("=" * 80)

    # Get all actively traded tickers
    tickers = get_actively_traded_tickers()
    logger.info(f"Found {len(tickers)} actively traded tickers to process")

    total_deleted = 0
    total_updated = 0
    errors = 0
    processed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ticker = {
            executor.submit(process_ticker, ticker_id, ticker_symbol, dry_run): ticker_symbol
            for ticker_id, ticker_symbol in tickers
        }

        # Process results as they complete
        for future in as_completed(future_to_ticker):
            ticker_symbol = future_to_ticker[future]
            processed += 1

            try:
                result = future.result()
                total_deleted += result.deleted
                total_updated += result.updated

                if result.error:
                    errors += 1
                elif result.deleted > 0 or result.updated > 0:
                    logger.info(
                        f"[{processed}/{len(tickers)}] {result.ticker}: "
                        f"deleted={result.deleted}, updated={result.updated}"
                    )

            except Exception as e:
                errors += 1
                logger.error(f"[{processed}/{len(tickers)}] {ticker_symbol}: Exception - {str(e)}")

            # Progress update every 500 tickers
            if processed % 500 == 0:
                logger.info(f"Progress: {processed}/{len(tickers)} tickers processed")

    # Summary
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total tickers processed: {processed}")
    logger.info(f"Total duplicates deleted: {total_deleted}")
    logger.info(f"Total periods updated: {total_updated}")
    logger.info(f"Errors: {errors}")
    if dry_run:
        logger.info("(DRY RUN - no changes were made)")
    logger.info("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix earnings transcript period formatting inconsistencies'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate changes without making them'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Number of parallel workers (default: 10)'
    )

    args = parser.parse_args()

    try:
        fix_all_transcript_periods(dry_run=args.dry_run, max_workers=args.workers)
        logger.info("\nScript completed successfully")

    except Exception as e:
        logger.error(f"\nScript failed: {str(e)}", exc_info=True)
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
