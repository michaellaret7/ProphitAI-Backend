"""Shared fixtures for prophitai-data test suite."""
import os

import pytest
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Set a valid Fernet encryption key for all tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("MESSAGE_ENCRYPTION_KEY", key)
    # Reset the cipher singleton so it picks up the new key
    import prophitai_data.internal.encryption as enc_mod
    enc_mod._cipher = None


@pytest.fixture(autouse=True)
def _set_db_urls(monkeypatch):
    """Set dummy database URLs so db_config module can load without real DB."""
    monkeypatch.setenv("MARKET_DATA", "postgresql://test:test@localhost:5432/test_market")
    monkeypatch.setenv("USER_DATA", "postgresql://test:test@localhost:5432/test_user")
    monkeypatch.setenv("PROPHIT_ALTS", "postgresql://test:test@localhost:5432/test_alts")
    monkeypatch.setenv("MACRO_DATA", "postgresql://test:test@localhost:5432/test_macro")
    monkeypatch.setenv("FMP_API_KEY", "test_fmp_key")
    monkeypatch.setenv("ALPACA_API_KEY", "test_alpaca_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test_alpaca_secret")
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "test_snap_id")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "test_snap_key")


# ================================
# --> Helper funcs
# ================================

def _make_mock_session():
    """Create a MagicMock that behaves like a SQLAlchemy session."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.filter_by.return_value = session
    session.join.return_value = session
    session.order_by.return_value = session
    session.limit.return_value = session
    session.offset.return_value = session
    session.all.return_value = []
    session.first.return_value = None
    session.count.return_value = 0
    return session


@pytest.fixture
def mock_market_session():
    """Return a mock SQLAlchemy session for the market database."""
    return _make_mock_session()


@pytest.fixture
def mock_user_session():
    """Return a mock SQLAlchemy session for the user database."""
    return _make_mock_session()


@pytest.fixture
def mock_prophit_session():
    """Return a mock SQLAlchemy session for the prophit alts database."""
    return _make_mock_session()


@pytest.fixture
def mock_macro_session():
    """Return a mock SQLAlchemy session for the macro database."""
    return _make_mock_session()
