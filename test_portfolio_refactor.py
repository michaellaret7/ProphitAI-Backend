"""
Test script to verify portfolio repository refactor works correctly.
Tests all CRUD operations with the new normalized schema (Portfolio + PortfolioItem).
"""
import uuid
from dataclasses import dataclass
from app.repositories.portfolio_data import (
    retrieve_portfolio,
    add_portfolio,
    list_portfolios,
    update_portfolio,
    delete_portfolio,
    get_all_portfolio_ids,
)
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User


@dataclass
class Position:
    """Mock Position object matching expected input format.

    Allocation is in decimal format: 0.25 = 25%
    """
    ticker: str
    allocation: float  # Decimal format (0.25 = 25%)


def get_test_user_id() -> uuid.UUID:
    """Get a valid user ID from the database for testing."""
    with UserSession() as session:
        user = session.query(User).first()
        if not user:
            raise ValueError("No users found in database. Please create a test user first.")
        return user.id


def test_add_portfolio(user_id: uuid.UUID, portfolio_name: str) -> None:
    """Test adding a new portfolio with positions."""
    print(f"\n{'='*60}")
    print("TEST: add_portfolio")
    print(f"{'='*60}")

    # Allocations in decimal format (0.30 = 30%)
    positions = [
        Position(ticker="AAPL", allocation=0.30),
        Position(ticker="MSFT", allocation=0.25),
        Position(ticker="GOOGL", allocation=0.25),
        Position(ticker="AMZN", allocation=0.20),
    ]

    try:
        add_portfolio(
            portfolio=positions,
            user_id=user_id,
            portfolio_name=portfolio_name
        )
        print(f"SUCCESS: Created portfolio '{portfolio_name}' with {len(positions)} positions")
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def test_list_portfolios(user_id: uuid.UUID) -> list:
    """Test listing all portfolios for a user."""
    print(f"\n{'='*60}")
    print("TEST: list_portfolios")
    print(f"{'='*60}")

    try:
        portfolios = list_portfolios(user_id=user_id)
        print(f"SUCCESS: Found {len(portfolios)} portfolio(s)")
        for p in portfolios:
            print(f"  - {p['name']} (id: {p['portfolio_id'][:8]}..., is_current: {p['is_current']})")
        return portfolios
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def test_retrieve_portfolio(user_id: uuid.UUID, portfolio_id: uuid.UUID = None) -> list:
    """Test retrieving portfolio with all positions in legacy flat format."""
    print(f"\n{'='*60}")
    print("TEST: retrieve_portfolio")
    print(f"{'='*60}")

    try:
        if portfolio_id:
            positions = retrieve_portfolio(portfolio_id=portfolio_id)
        else:
            positions = retrieve_portfolio(user_id=user_id)

        print(f"SUCCESS: Retrieved {len(positions)} position(s)")

        # Verify legacy format fields are present
        if positions:
            pos = positions[0]
            required_fields = ['portfolio_id', 'name', 'ticker', 'allocation',
                             'sector', 'industry', 'sub_industry', 'is_current',
                             'user_id']
            missing = [f for f in required_fields if f not in pos]
            if missing:
                print(f"WARNING: Missing fields in output: {missing}")
            else:
                print("SUCCESS: All required legacy fields present")

            # Print sample position
            print(f"\nSample position:")
            for key in required_fields:
                print(f"  {key}: {pos.get(key)}")

        return positions
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def test_update_portfolio(user_id: uuid.UUID, portfolio_id: uuid.UUID) -> None:
    """Test updating portfolio metadata and positions."""
    print(f"\n{'='*60}")
    print("TEST: update_portfolio")
    print(f"{'='*60}")

    # Test 1: Update metadata only
    try:
        result = update_portfolio(
            user_id=user_id,
            portfolio_id=portfolio_id,
            name="Updated Test Portfolio",
            is_current=True
        )
        if result:
            print("SUCCESS: Updated portfolio metadata (name, is_current)")
        else:
            print("FAILED: update_portfolio returned False")
    except Exception as e:
        print(f"FAILED: {e}")
        raise

    # Test 2: Update positions (allocations in decimal format)
    try:
        new_positions = {
            "AAPL": 0.40,
            "MSFT": 0.35,
            "NVDA": 0.25,
        }
        result = update_portfolio(
            user_id=user_id,
            portfolio_id=portfolio_id,
            positions=new_positions
        )
        if result:
            print(f"SUCCESS: Replaced positions with {len(new_positions)} new positions")
        else:
            print("FAILED: update_portfolio returned False")
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def test_get_all_portfolio_ids(user_id: uuid.UUID) -> list:
    """Test getting all portfolio IDs for a user."""
    print(f"\n{'='*60}")
    print("TEST: get_all_portfolio_ids")
    print(f"{'='*60}")

    try:
        ids = get_all_portfolio_ids(user_id=user_id)
        print(f"SUCCESS: Found {len(ids)} portfolio ID(s)")
        for pid in ids:
            print(f"  - {str(pid)[:8]}...")
        return ids
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def test_delete_portfolio(user_id: uuid.UUID, portfolio_id: uuid.UUID) -> None:
    """Test deleting a portfolio."""
    print(f"\n{'='*60}")
    print("TEST: delete_portfolio")
    print(f"{'='*60}")

    try:
        result = delete_portfolio(
            user_id=user_id,
            portfolio_id=portfolio_id
        )
        if result:
            print(f"SUCCESS: Deleted portfolio {str(portfolio_id)[:8]}...")
        else:
            print("FAILED: delete_portfolio returned False")
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def run_all_tests():
    """Run all portfolio repository tests."""
    print("\n" + "="*60)
    print("PORTFOLIO REPOSITORY REFACTOR - INTEGRATION TESTS")
    print("="*60)

    # Get a test user
    user_id = get_test_user_id()
    print(f"\nUsing test user ID: {user_id}")

    test_portfolio_name = f"Test Portfolio {uuid.uuid4().hex[:8]}"
    created_portfolio_id = None

    try:
        # Test 1: Add portfolio
        test_add_portfolio(user_id, test_portfolio_name)

        # Test 2: List portfolios (should include new one)
        portfolios = test_list_portfolios(user_id)

        # Find the portfolio we just created
        created = next((p for p in portfolios if p['name'] == test_portfolio_name), None)
        if created:
            created_portfolio_id = uuid.UUID(created['portfolio_id'])
            print(f"\nFound created portfolio: {created_portfolio_id}")
        else:
            print("WARNING: Could not find created portfolio in list")
            return

        # Test 3: Retrieve portfolio by ID
        positions = test_retrieve_portfolio(user_id, created_portfolio_id)

        # Verify position count
        if len(positions) == 4:
            print("SUCCESS: Correct number of positions (4)")
        else:
            print(f"WARNING: Expected 4 positions, got {len(positions)}")

        # Test 4: Get all portfolio IDs
        test_get_all_portfolio_ids(user_id)

        # Test 5: Update portfolio
        test_update_portfolio(user_id, created_portfolio_id)

        # Verify update worked
        positions_after_update = test_retrieve_portfolio(user_id, created_portfolio_id)
        if len(positions_after_update) == 3:
            print("SUCCESS: Position count updated correctly (3)")
        else:
            print(f"WARNING: Expected 3 positions after update, got {len(positions_after_update)}")

        # Test 6: Delete portfolio
        test_delete_portfolio(user_id, created_portfolio_id)

        # Verify deletion
        positions_after_delete = retrieve_portfolio(portfolio_id=created_portfolio_id)
        if len(positions_after_delete) == 0:
            print("SUCCESS: Portfolio deleted successfully (no positions returned)")
        else:
            print(f"WARNING: Portfolio still has {len(positions_after_delete)} positions after delete")

        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"TEST SUITE FAILED: {e}")
        print(f"{'='*60}\n")

        # Cleanup: try to delete the test portfolio if it was created
        if created_portfolio_id:
            try:
                delete_portfolio(user_id=user_id, portfolio_id=created_portfolio_id)
                print("Cleaned up test portfolio")
            except:
                pass
        raise


if __name__ == "__main__":
    run_all_tests()
