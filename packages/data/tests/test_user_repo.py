"""Tests for user account repository functions.

Validates get_all_user_data, email_exists, and add_user with mocked sessions.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch


# ================================
# --> Helper funcs
# ================================

def _make_mock_session(return_user=None):
    """Create a mock SQLAlchemy session with chainable query methods."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.options.return_value = session
    session.first.return_value = return_user
    return session


def _mock_get_session_class(mock_session):
    """Return a factory that yields a callable returning mock_session."""
    def _factory(session_type):
        return lambda: mock_session
    return _factory


def _make_mock_user(with_portfolios=False):
    """Create a mock User object with optional portfolios."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.clerk_id = "clerk_abc"
    user.email = "alice@example.com"
    user.first_name = "Alice"
    user.last_name = "Smith"
    user.broker = "snaptrade"
    user.snaptrade_account_id = "acct_123"
    user.creation_date = MagicMock()
    user.creation_date.isoformat.return_value = "2026-01-01T00:00:00"

    if with_portfolios:
        portfolio = MagicMock()
        portfolio.name = "Growth Fund"
        portfolio.id = uuid.uuid4()
        portfolio.nav = 50000.0
        portfolio.is_current = True
        portfolio.is_discretionary = False
        user.portfolios = [portfolio]
    else:
        user.portfolios = []

    return user


class TestGetAllUserData:
    """Tests for get_all_user_data."""

    @patch("prophitai_data.repositories.user.account.selectinload", return_value=MagicMock())
    @patch("prophitai_data.session.decorators._get_session_class")
    def test_get_all_user_data_found(self, mock_gsc, _mock_load):
        """Returns formatted dict when user with portfolios is found."""
        user = _make_mock_user(with_portfolios=True)
        session = _make_mock_session(return_user=user)
        # Reason: options() must chain back to the queryable session mock
        session.options.return_value = session
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.user.account import get_all_user_data
        from prophitai_data.db.models.user import User
        # Reason: User.portfolios relationship isn't available without DB,
        # so we temporarily add it as a descriptor for selectinload
        User.portfolios = MagicMock()
        try:
            result = get_all_user_data(email="alice@example.com")
        finally:
            del User.portfolios

        assert result is not None
        assert result["email"] == "alice@example.com"
        assert result["first_name"] == "Alice"
        assert len(result["portfolios"]) == 1
        assert result["portfolios"][0]["name"] == "Growth Fund"
        assert result["portfolios"][0]["nav"] == pytest.approx(50000.0)

    @patch("prophitai_data.repositories.user.account.selectinload", return_value=MagicMock())
    @patch("prophitai_data.session.decorators._get_session_class")
    def test_get_all_user_data_not_found(self, mock_gsc, _mock_load):
        """Returns None when user is not found."""
        session = _make_mock_session(return_user=None)
        session.options.return_value = session
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.user.account import get_all_user_data
        from prophitai_data.db.models.user import User
        # Reason: User.portfolios relationship isn't available without DB
        User.portfolios = MagicMock()
        try:
            result = get_all_user_data(email="nobody@example.com")
        finally:
            del User.portfolios

        assert result is None


class TestEmailExists:
    """Tests for email_exists."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_email_exists_true(self, mock_gsc):
        """Returns True when user with email is found."""
        user = _make_mock_user()
        session = _make_mock_session(return_user=user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.user.account import email_exists
        assert email_exists(email="alice@example.com") is True

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_email_exists_false(self, mock_gsc):
        """Returns False when no user with email is found."""
        session = _make_mock_session(return_user=None)
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.user.account import email_exists
        assert email_exists(email="nobody@example.com") is False

    def test_email_exists_empty_string(self):
        """Returns False for empty email without hitting the DB."""
        # Reason: The function has an early return for falsy email
        from prophitai_data.repositories.user.account import email_exists
        assert email_exists(email="") is False


class TestAddUser:
    """Tests for add_user."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_add_user_creates_new(self, mock_gsc):
        """When user does not exist, creates and returns new User."""
        session = _make_mock_session(return_user=None)
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.user.account import add_user
        result = add_user(
            email="new@example.com",
            first_name="New",
            last_name="User",
            clerk_id="clerk_new",
        )

        # Reason: add_user creates a User object and adds it to session
        assert session.add.called
        added_user = session.add.call_args[0][0]
        assert added_user.email == "new@example.com"
        assert added_user.first_name == "New"
        assert added_user.last_name == "User"

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_add_user_returns_existing(self, mock_gsc):
        """When user already exists, returns existing user without creating."""
        existing_user = _make_mock_user()
        session = _make_mock_session(return_user=existing_user)
        mock_gsc.side_effect = _mock_get_session_class(session)

        from prophitai_data.repositories.user.account import add_user
        result = add_user(
            email="alice@example.com",
            first_name="Alice",
            last_name="Smith",
        )

        # Reason: Existing user is returned, session.add is NOT called
        assert result is existing_user
        assert not session.add.called
