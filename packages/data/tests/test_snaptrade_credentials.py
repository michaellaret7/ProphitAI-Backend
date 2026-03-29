"""Tests for SnapTrade credential resolution functions.

Validates resolve_snaptrade_credentials, resolve_broker_account,
resolve_snaptrade_auth, and get_snaptrade_broker with mocked DB sessions.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

# Reason: snaptrade_client is not installed in test env, so we must
# stub out the import chain before the module is first loaded.
sys.modules.setdefault("snaptrade_client", MagicMock())
sys.modules.setdefault("prophitai_data.clients.snaptrade.client", MagicMock())
sys.modules.setdefault("prophitai_data.clients.snaptrade.broker", MagicMock())

import prophitai_data.clients.snaptrade.credentials as creds_mod
from prophitai_data.clients.snaptrade.credentials import (
    resolve_snaptrade_credentials,
    resolve_broker_account,
    resolve_snaptrade_auth,
    get_snaptrade_broker,
)


# ================================
# --> Helper funcs
# ================================

def _make_mock_user(**overrides):
    """Create a mock User with SnapTrade fields."""
    user = MagicMock()
    user.snaptrade_user_id = overrides.get("snaptrade_user_id", "snap_uid_123")
    user.snaptrade_user_secret = overrides.get("snaptrade_user_secret", "snap_secret_abc")
    user.snaptrade_account_id = overrides.get("snaptrade_account_id", "snap_acct_456")
    user.clerk_id = overrides.get("clerk_id", "clerk_001")
    user.email = overrides.get("email", "test@example.com")
    user.id = overrides.get("id", "uuid-001")
    return user


def _make_mock_session(return_user=None):
    """Create a mock SQLAlchemy session that chains query/filter/first."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = return_user
    return session


def _mock_get_session_class(mock_session):
    """Return a factory function that yields a callable returning mock_session."""
    def _factory(session_type):
        # Reason: The decorator calls session_cls() to create a session instance
        return lambda: mock_session
    return _factory


class TestResolveSnaptradeCredentials:
    """Tests for resolve_snaptrade_credentials."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_resolve_by_clerk_id(self, mock_gsc):
        """Resolving by clerk_id returns all three credential fields."""
        user = _make_mock_user()
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        result = resolve_snaptrade_credentials(clerk_id="clerk_001")

        assert result["snaptrade_user_id"] == "snap_uid_123"
        assert result["snaptrade_user_secret"] == "snap_secret_abc"
        assert result["snaptrade_account_id"] == "snap_acct_456"

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_resolve_by_email(self, mock_gsc):
        """Resolving by email returns all three credential fields."""
        user = _make_mock_user(email="alice@test.com")
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        result = resolve_snaptrade_credentials(email="alice@test.com")

        assert result["snaptrade_user_id"] == "snap_uid_123"
        assert result["snaptrade_user_secret"] == "snap_secret_abc"
        assert result["snaptrade_account_id"] == "snap_acct_456"

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_no_identifier_raises(self, mock_gsc):
        """Passing no identifiers raises ValueError."""
        session = _make_mock_session()
        mock_gsc.side_effect = _mock_get_session_class(session)

        with pytest.raises(ValueError, match="At least one identifier"):
            resolve_snaptrade_credentials()

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_user_not_found_raises(self, mock_gsc):
        """Missing user raises ValueError."""
        session = _make_mock_session(return_user=None)
        mock_gsc.side_effect = _mock_get_session_class(session)

        with pytest.raises(ValueError, match="User not found"):
            resolve_snaptrade_credentials(clerk_id="nonexistent")

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_missing_credentials_raises(self, mock_gsc):
        """User without snaptrade_user_id raises ValueError."""
        user = _make_mock_user(snaptrade_user_id=None, snaptrade_user_secret=None)
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        with pytest.raises(ValueError, match="missing SnapTrade authentication"):
            resolve_snaptrade_credentials(clerk_id="clerk_001")

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_missing_account_id_raises(self, mock_gsc):
        """User with credentials but no account_id raises ValueError."""
        user = _make_mock_user(snaptrade_account_id=None)
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        with pytest.raises(ValueError, match="missing SnapTrade account ID"):
            resolve_snaptrade_credentials(clerk_id="clerk_001")


class TestResolveBrokerAccount:
    """Tests for resolve_broker_account."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_returns_account_id_string(self, mock_gsc):
        """resolve_broker_account returns just the account_id string."""
        user = _make_mock_user()
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        result = resolve_broker_account(clerk_id="clerk_001")

        assert result == "snap_acct_456"
        assert isinstance(result, str)


class TestResolveSnaptradeAuth:
    """Tests for resolve_snaptrade_auth (no account_id required)."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_auth_without_account_id(self, mock_gsc):
        """resolve_snaptrade_auth works without snaptrade_account_id."""
        # Reason: This function is used during OAuth flow before account is linked
        user = _make_mock_user(snaptrade_account_id=None)
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        result = resolve_snaptrade_auth(clerk_id="clerk_001")

        assert result["snaptrade_user_id"] == "snap_uid_123"
        assert result["snaptrade_user_secret"] == "snap_secret_abc"
        assert "snaptrade_account_id" not in result


class TestGetSnaptradeBroker:
    """Tests for get_snaptrade_broker singleton."""

    def test_returns_singleton(self):
        """get_snaptrade_broker returns the same instance on repeated calls."""
        # Reason: Reset the module-level singleton before testing
        creds_mod._snaptrade_instance = None

        mock_broker_cls = MagicMock()
        mock_instance = MagicMock()
        mock_broker_cls.return_value = mock_instance

        with patch.dict(sys.modules, {
            "prophitai_data.clients.snaptrade.broker": MagicMock(
                SnapTradeBroker=mock_broker_cls
            ),
        }):
            first = get_snaptrade_broker()
            second = get_snaptrade_broker()

        assert first is second

        # Reason: Clean up singleton to avoid leaking state to other tests
        creds_mod._snaptrade_instance = None
