"""
Tests for session management decorators.

Verifies that @with_session, @with_transaction, and @with_sessions correctly
create, inject, commit/rollback, and close SQLAlchemy sessions.
"""

import pytest
from unittest.mock import MagicMock, patch

from prophitai_data.session.decorators import (
    with_session,
    with_transaction,
    with_sessions,
    _get_session_class,
)


# ================================
# --> Helper funcs
# ================================

def _make_mock_session_class():
    """Create a mock session factory that returns a mock session instance."""
    mock_session = MagicMock()
    mock_class = MagicMock(return_value=mock_session)
    return mock_class, mock_session


PATCH_TARGET = 'prophitai_data.session.decorators._get_session_class'


class TestGetSessionClass:
    """Verify _get_session_class maps types correctly and rejects unknowns."""

    def test_invalid_session_type_raises(self):
        """Unsupported session type should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported session_type"):
            _get_session_class('invalid_type')

    def test_valid_types_do_not_raise(self):
        """All supported session types should resolve without error."""
        for session_type in ('market', 'user', 'prophit', 'macro'):
            # Reason: Should not raise for any valid key
            result = _get_session_class(session_type)
            assert result is not None


class TestWithSession:
    """Verify @with_session creates, injects, and closes sessions."""

    def test_creates_and_injects_session(self):
        """Session should be created and passed to the function."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_session('market')
            def my_func(session=None):
                return session

            result = my_func()
            assert result is mock_session
            mock_cls.assert_called_once()

    def test_closes_session_on_success(self):
        """Session should be closed even when the function succeeds."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_session('market')
            def my_func(session=None):
                return "ok"

            my_func()
            mock_session.close.assert_called_once()

    def test_closes_session_on_exception(self):
        """Session should be closed even when the function raises."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_session('market')
            def my_func(session=None):
                raise ValueError("boom")

            with pytest.raises(ValueError, match="boom"):
                my_func()
            mock_session.close.assert_called_once()

    def test_respects_externally_provided_session(self):
        """When session is passed explicitly, decorator should NOT create one."""
        external = MagicMock()

        @with_session('market')
        def my_func(session=None):
            return session

        result = my_func(session=external)
        assert result is external
        external.close.assert_not_called()

    def test_passes_through_args_and_kwargs(self):
        """Positional and keyword args should reach the wrapped function."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_session('market')
            def my_func(a, b, session=None):
                return (a, b, session)

            result = my_func(1, b=2)
            assert result == (1, 2, mock_session)


class TestWithTransaction:
    """Verify @with_transaction commits on success, rolls back on error."""

    def test_commits_on_success(self):
        """Session should be committed when the function succeeds."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_transaction('user')
            def my_func(session=None):
                return "ok"

            result = my_func()
            assert result == "ok"
            mock_session.commit.assert_called_once()

    def test_closes_session_on_success(self):
        """Session should be closed after a successful commit."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_transaction('user')
            def my_func(session=None):
                return "ok"

            my_func()
            mock_session.close.assert_called_once()

    def test_rollback_on_exception(self):
        """Session should be rolled back when the function raises."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_transaction('user')
            def my_func(session=None):
                raise RuntimeError("fail")

            with pytest.raises(RuntimeError, match="fail"):
                my_func()
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    def test_no_commit_on_exception(self):
        """Commit should NOT be called when the function raises."""
        mock_cls, mock_session = _make_mock_session_class()

        with patch(PATCH_TARGET, return_value=mock_cls):
            @with_transaction('user')
            def my_func(session=None):
                raise RuntimeError("fail")

            with pytest.raises(RuntimeError):
                my_func()
            mock_session.commit.assert_not_called()

    def test_respects_externally_provided_session(self):
        """External session should not be committed, rolled back, or closed."""
        external = MagicMock()

        @with_transaction('market')
        def my_func(session=None):
            return "ok"

        my_func(session=external)
        external.commit.assert_not_called()
        external.rollback.assert_not_called()
        external.close.assert_not_called()


class TestWithSessions:
    """Verify @with_sessions injects multiple named sessions."""

    def test_injects_multiple_sessions(self):
        """Each requested session type should be created and injected."""
        mock_market_cls, mock_market = _make_mock_session_class()
        mock_user_cls, mock_user = _make_mock_session_class()

        def fake_get_session_class(session_type):
            if session_type == 'market':
                return mock_market_cls
            elif session_type == 'user':
                return mock_user_cls

        with patch(PATCH_TARGET, side_effect=fake_get_session_class):
            @with_sessions(market_session='market', user_session='user')
            def my_func(market_session=None, user_session=None):
                return market_session, user_session

            m, u = my_func()
            assert m is mock_market
            assert u is mock_user

    def test_closes_all_sessions(self):
        """All created sessions should be closed after execution."""
        mock_market_cls, mock_market = _make_mock_session_class()
        mock_user_cls, mock_user = _make_mock_session_class()

        def fake_get_session_class(session_type):
            return mock_market_cls if session_type == 'market' else mock_user_cls

        with patch(PATCH_TARGET, side_effect=fake_get_session_class):
            @with_sessions(market_session='market', user_session='user')
            def my_func(market_session=None, user_session=None):
                pass

            my_func()
            mock_market.close.assert_called_once()
            mock_user.close.assert_called_once()

    def test_closes_sessions_on_exception(self):
        """All created sessions should be closed even when the function raises."""
        mock_market_cls, mock_market = _make_mock_session_class()
        mock_user_cls, mock_user = _make_mock_session_class()

        def fake_get_session_class(session_type):
            return mock_market_cls if session_type == 'market' else mock_user_cls

        with patch(PATCH_TARGET, side_effect=fake_get_session_class):
            @with_sessions(market_session='market', user_session='user')
            def my_func(market_session=None, user_session=None):
                raise RuntimeError("fail")

            with pytest.raises(RuntimeError):
                my_func()
            mock_market.close.assert_called_once()
            mock_user.close.assert_called_once()

    def test_respects_externally_provided_session(self):
        """Externally provided sessions should not be overwritten or closed."""
        mock_market_cls, mock_market = _make_mock_session_class()
        external_user = MagicMock()

        with patch(PATCH_TARGET, return_value=mock_market_cls):
            @with_sessions(market_session='market', user_session='user')
            def my_func(market_session=None, user_session=None):
                return market_session, user_session

            m, u = my_func(user_session=external_user)
            assert m is mock_market
            assert u is external_user
            external_user.close.assert_not_called()
