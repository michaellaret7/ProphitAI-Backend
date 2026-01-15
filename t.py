"""Test script for batch portfolio positions endpoint."""

import uuid
from app.repositories.portfolio_data import (
    retrieve_portfolios_batch,
    list_portfolios,
    retrieve_portfolio,
)


def test_batch_positions():
    """Test the retrieve_portfolios_batch function."""

    # First, get some portfolio IDs from an existing user
    # Using Michael's user_id from the codebase
    user_id = uuid.UUID("b]f6a9a3-7e4d-4c8b-9f1e-2d3c4b5a6789")  # placeholder

    # List all portfolios to get valid IDs
    print("Fetching portfolio list...")
    portfolios = list_portfolios(user_id=user_id)

    if not portfolios:
        print("No portfolios found for user. Testing with empty list...")
        result = retrieve_portfolios_batch(portfolio_ids=[])
        print(f"Empty batch result: {result}")
        return

    print(f"Found {len(portfolios)} portfolios:")
    for p in portfolios:
        print(f"  - {p['portfolio_id']}: {p['name']}")

    # Get the first 3 portfolio IDs (or all if less than 3)
    portfolio_ids = [uuid.UUID(p['portfolio_id']) for p in portfolios[:3]]
    print(f"\nTesting batch fetch with {len(portfolio_ids)} portfolios...")

    # Test batch retrieval
    result = retrieve_portfolios_batch(portfolio_ids=portfolio_ids)

    print(f"\nBatch positions result:")
    print(f"  Portfolios returned: {len(result)}")

    for pid, positions in result.items():
        print(f"\n  Portfolio {pid}:")
        print(f"    Positions: {len(positions)}")
        if positions:
            print(f"    First position: {positions[0]['ticker']} @ {positions[0]['allocation']:.2%}")
            print(f"    Sectors: {set(p['sector'] for p in positions if p['sector'])}")


def test_single_vs_batch():
    """Compare single retrieval vs batch retrieval for consistency."""

    # Get portfolios from the database
    print("\n" + "="*60)
    print("Testing single vs batch consistency...")
    print("="*60)

    # We need to get portfolio IDs - let's query directly
    from app.db.core.db_config import UserSession
    from app.db.core.models.user_data_models import Portfolio

    with UserSession() as session:
        portfolios = session.query(Portfolio).limit(3).all()
        portfolio_ids = [p.id for p in portfolios]

    if not portfolio_ids:
        print("No portfolios in database to test.")
        return

    print(f"Found {len(portfolio_ids)} portfolios to test")

    # Get positions individually
    print("\nFetching positions individually...")
    individual_results = {}
    for pid in portfolio_ids:
        positions = retrieve_portfolio(portfolio_id=pid)
        individual_results[str(pid)] = positions
        print(f"  Portfolio {pid}: {len(positions)} positions")

    # Get positions in batch
    print("\nFetching positions in batch...")
    batch_results = retrieve_portfolios_batch(portfolio_ids=portfolio_ids)
    print(f"  Batch returned {len(batch_results)} portfolios")

    # Compare results
    print("\nComparing results...")
    all_match = True
    for pid_str, individual_positions in individual_results.items():
        batch_positions = batch_results.get(pid_str, [])

        # Compare position counts
        if len(individual_positions) != len(batch_positions):
            print(f"  MISMATCH {pid_str}: individual={len(individual_positions)}, batch={len(batch_positions)}")
            all_match = False
        else:
            # Compare tickers
            individual_tickers = set(p['ticker'] for p in individual_positions)
            batch_tickers = set(p['ticker'] for p in batch_positions)
            if individual_tickers != batch_tickers:
                print(f"  TICKER MISMATCH {pid_str}: {individual_tickers} vs {batch_tickers}")
                all_match = False
            else:
                print(f"  MATCH {pid_str}: {len(batch_positions)} positions")

    if all_match:
        print("\nAll results match!")
    else:
        print("\nSome results did not match!")


if __name__ == "__main__":
    test_single_vs_batch()
