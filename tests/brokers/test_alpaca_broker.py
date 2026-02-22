"""
Integration tests for Alpaca Broker API module.
Runs against the Alpaca sandbox using env vars ALPACA_BROKER_API_KEY / ALPACA_BROKER_SECRET_KEY.

Usage:
    pytest tests/brokers/test_alpaca_broker.py -v
"""

import os
import time
import pytest

from app.brokers.alpaca_broker import ProphitBroker

SKIP_REASON = "ALPACA_BROKER_API_KEY not set — skipping sandbox integration tests"
HAS_KEYS = bool(os.getenv("ALPACA_BROKER_API_KEY") and os.getenv("ALPACA_BROKER_SECRET_KEY"))

pytestmark = pytest.mark.skipif(not HAS_KEYS, reason=SKIP_REASON)


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def broker() -> ProphitBroker:
    """Create a single ProphitBroker instance for all tests in the module."""
    return ProphitBroker(sandbox=True)


@pytest.fixture(scope="module")
def test_account_id(broker: ProphitBroker) -> str:
    """Get the first available account ID for testing."""
    accounts = broker.list_accounts()
    assert len(accounts) > 0, "No accounts found in sandbox — create one first"
    return accounts[0]["account_id"]


# ════════════════════════════════════════════════════════════
# Accounts
# ════════════════════════════════════════════════════════════

class TestAccounts:
    """Test account query operations."""

    def test_list_accounts(self, broker: ProphitBroker):
        accounts = broker.list_accounts()
        assert isinstance(accounts, list)
        if accounts:
            acct = accounts[0]
            assert "account_id" in acct
            assert "status" in acct

    def test_get_account(self, broker: ProphitBroker, test_account_id: str):
        acct = broker.get_account(test_account_id)
        assert acct["account_id"] == test_account_id
        assert "cash" in acct
        assert "equity" in acct
        assert "buying_power" in acct

    def test_get_account_activities(self, broker: ProphitBroker, test_account_id: str):
        activities = broker.get_account_activities(test_account_id)
        assert isinstance(activities, list)


# ════════════════════════════════════════════════════════════
# Trading
# ════════════════════════════════════════════════════════════

class TestTrading:
    """Test order execution and management."""

    def test_buy_market_order(self, broker: ProphitBroker, test_account_id: str):
        order = broker.buy(test_account_id, "AAPL", qty=1)
        assert order["symbol"] == "AAPL"
        assert order["side"] == "OrderSide.BUY"
        assert order["id"] is not None

    def test_get_orders_with_status(self, broker: ProphitBroker, test_account_id: str):
        # Reason: small delay to let the order propagate
        time.sleep(1)
        orders = broker.get_orders(test_account_id, status="all")
        assert isinstance(orders, list)
        assert len(orders) > 0

    def test_get_orders_open(self, broker: ProphitBroker, test_account_id: str):
        orders = broker.get_orders(test_account_id, status="open")
        assert isinstance(orders, list)

    def test_cancel_order(self, broker: ProphitBroker, test_account_id: str):
        """Place a limit order far from market, then cancel it."""
        order = broker.buy(
            test_account_id, "AAPL", qty=1, limit_price=1.00, time_in_force="gtc",
        )
        order_id = order["id"]
        time.sleep(1)
        broker.cancel_order(test_account_id, order_id)

    def test_get_positions(self, broker: ProphitBroker, test_account_id: str):
        positions = broker.get_positions(test_account_id)
        assert isinstance(positions, list)


# ════════════════════════════════════════════════════════════
# Portfolio
# ════════════════════════════════════════════════════════════

class TestPortfolio:
    """Test portfolio and asset operations."""

    def test_get_portfolio_history(self, broker: ProphitBroker, test_account_id: str):
        history = broker.get_portfolio_history(test_account_id, period="1M", timeframe="1D")
        assert "timestamp" in history
        assert "equity" in history

    def test_get_asset(self, broker: ProphitBroker):
        asset = broker.get_asset("AAPL")
        assert asset["symbol"] == "AAPL"
        assert asset["tradable"] is True


# ════════════════════════════════════════════════════════════
# Funding
# ════════════════════════════════════════════════════════════

class TestFunding:
    """Test funding query operations."""

    def test_get_transfers(self, broker: ProphitBroker, test_account_id: str):
        transfers = broker.get_transfers(test_account_id)
        assert isinstance(transfers, list)

    def test_get_journals(self, broker: ProphitBroker):
        journals = broker.get_journals()
        assert isinstance(journals, list)


# ════════════════════════════════════════════════════════════
# Watchlists
# ════════════════════════════════════════════════════════════

class TestWatchlists:
    """Test watchlist CRUD."""

    def test_watchlist_lifecycle(self, broker: ProphitBroker, test_account_id: str):
        """Create, add symbol, verify, and delete a watchlist."""
        # Create
        wl = broker.create_watchlist(test_account_id, "Test WL", symbols=["AAPL"])
        wl_id = wl["watchlist_id"]
        assert wl["name"] == "Test WL"
        assert "AAPL" in wl["symbols"]

        # Add symbol
        wl = broker.add_symbol_to_watchlist(test_account_id, wl_id, "MSFT")
        assert "MSFT" in wl["symbols"]

        # Get all watchlists
        all_wls = broker.get_watchlists(test_account_id)
        assert isinstance(all_wls, list)
        assert any(w["watchlist_id"] == wl_id for w in all_wls)

        # Delete
        broker.delete_watchlist(test_account_id, wl_id)


# ════════════════════════════════════════════════════════════
# Documents
# ════════════════════════════════════════════════════════════

class TestDocuments:
    """Test document retrieval."""

    def test_get_documents(self, broker: ProphitBroker, test_account_id: str):
        docs = broker.get_documents(test_account_id)
        assert isinstance(docs, list)
