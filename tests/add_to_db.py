"""
Script to delete all portfolios created before today.

This script:
1. Queries all portfolios created before today's date
2. Displays portfolios to be deleted
3. Deletes them from the database (with confirmation)
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, date
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio
from typing import List


def get_portfolios_before_date(cutoff_date: date, session) -> List[Portfolio]:
    """
    Query portfolios created before the cutoff date.

    Args:
        cutoff_date: Date to filter portfolios by (exclusive)
        session: Database session

    Returns:
        List of Portfolio objects created before cutoff date
    """
    portfolios = session.query(Portfolio).filter(
        Portfolio.created_date < datetime.combine(cutoff_date, datetime.min.time())
    ).all()

    return portfolios


def delete_portfolios_before_today(dry_run: bool = True) -> dict:
    """
    Delete all portfolios created before today.

    Args:
        dry_run: If True, only show what would be deleted without committing

    Returns:
        Dictionary with deletion statistics
    """
    session = UserSession()
    today = date.today()

    stats = {
        'total_deleted': 0,
        'unique_portfolio_ids': set(),
        'portfolios_by_name': {}
    }

    try:
        # Get portfolios created before today
        portfolios = get_portfolios_before_date(today, session)

        print(f"\n{'='*80}")
        print(f"DELETE PORTFOLIOS BEFORE TODAY")
        print(f"{'='*80}")
        print(f"Today's Date: {today}")
        print(f"Mode: {'DRY RUN (no deletions will occur)' if dry_run else 'LIVE (deletions will be committed)'}")
        print(f"Found {len(portfolios)} portfolio records created before {today}")
        print(f"{'='*80}\n")

        if not portfolios:
            print("[INFO] No portfolios found created before today.")
            return stats

        # Group portfolios by portfolio_id and name
        for portfolio in portfolios:
            stats['unique_portfolio_ids'].add(portfolio.portfolio_id)
            portfolio_name = portfolio.name

            if portfolio_name not in stats['portfolios_by_name']:
                stats['portfolios_by_name'][portfolio_name] = {
                    'count': 0,
                    'tickers': [],
                    'portfolio_id': portfolio.portfolio_id,
                    'created_date': portfolio.created_date
                }

            stats['portfolios_by_name'][portfolio_name]['count'] += 1
            stats['portfolios_by_name'][portfolio_name]['tickers'].append(portfolio.ticker)

        # Display portfolios to be deleted
        print(f"PORTFOLIOS TO BE DELETED:")
        print(f"{'-'*80}")
        for idx, (name, info) in enumerate(sorted(stats['portfolios_by_name'].items()), 1):
            print(f"\n{idx}. {name}")
            print(f"   Portfolio ID: {info['portfolio_id']}")
            print(f"   Created Date: {info['created_date']}")
            print(f"   Holdings: {info['count']}")
            print(f"   Tickers: {', '.join(info['tickers'][:10])}")
            if info['count'] > 10:
                print(f"            ... and {info['count'] - 10} more")

        print(f"\n{'='*80}")
        print(f"SUMMARY:")
        print(f"  - Unique Portfolios: {len(stats['unique_portfolio_ids'])}")
        print(f"  - Total Holdings (records): {len(portfolios)}")
        print(f"{'='*80}\n")

        # Delete portfolios
        if not dry_run:
            stats['total_deleted'] = len(portfolios)
            for portfolio in portfolios:
                session.delete(portfolio)

            session.commit()
            print(f"[SUCCESS] Deleted {stats['total_deleted']} portfolio records from database")
        else:
            session.rollback()
            print(f"[DRY RUN] No deletions performed (rollback)")

        return stats

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Error deleting portfolios: {str(e)}")
        import traceback
        traceback.print_exc()
        return stats

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Delete all portfolios created before today'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply deletions (default is dry-run mode)'
    )
    args = parser.parse_args()

    if args.apply:
        # Run in live mode
        print("\n" + "="*80)
        print("WARNING: LIVE MODE - Deletions will be permanent!")
        print("="*80)
        delete_portfolios_before_today(dry_run=False)
    else:
        # Run in dry-run mode
        print("\n" + "="*80)
        print("DRY RUN - Preview Deletions")
        print("="*80)
        stats = delete_portfolios_before_today(dry_run=True)

        if stats['total_deleted'] == 0 and len(stats['unique_portfolio_ids']) > 0:
            print("\n" + "="*80)
            print(f"Found {len(stats['unique_portfolio_ids'])} portfolios to delete.")
            print("="*80)
            print("\nTo permanently delete these portfolios, run:")
            print("  python tests/add_to_db.py --apply")
        elif len(stats['unique_portfolio_ids']) == 0:
            print("\n[INFO] No portfolios found to delete.")
