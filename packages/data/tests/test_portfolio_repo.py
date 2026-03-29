"""Tests for portfolio repository CRUD and retrieval operations.

Validates add_portfolio raises ValueError when num_shares/position_nav
are missing, and tests list_portfolios with mocked sessions.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch


# ================================
# --> Helper funcs
# ================================

def _make_mock_session(return_user=None, return_ticker=None):
    """Create a mock SQLAlchemy session with chainable query methods."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = return_user
    session.all.return_value = []
    return session


def _make_mock_user(user_id=None):
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    return user


def _make_position(ticker, allocation, num_shares=None, position_nav=None):
    """Create a mock position object with optional computed fields."""
    pos = MagicMock()
    pos.ticker = ticker
    pos.allocation = allocation
    pos.num_shares = num_shares
    pos.position_nav = position_nav
    return pos


def _mock_get_session_class(user_session, market_session=None):
    """Return a factory that maps session types to mock sessions."""
    def _factory(session_type):
        if session_type == "user":
            return lambda: user_session
        elif session_type == "market":
            return lambda: market_session or MagicMock()
        return lambda: MagicMock()
    return _factory


class TestAddPortfolioComplete:
    """Tests for add_portfolio with complete position data."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_add_portfolio_with_complete_positions(self, mock_gsc):
        """Positions with num_shares + position_nav succeed without API calls."""
        user = _make_mock_user()
        user_session = _make_mock_session(return_user=user)

        # Reason: Market session must return a Ticker for validation
        market_session = MagicMock()
        market_session.query.return_value = market_session
        market_session.filter.return_value = market_session
        market_session.first.return_value = MagicMock(ticker="AAPL")

        mock_gsc.side_effect = _mock_get_session_class(user_session, market_session)

        from prophitai_data.repositories.portfolio.crud import add_portfolio

        positions = [
            _make_position("AAPL", 0.60, num_shares=100, position_nav=15000.0),
            _make_position("MSFT", 0.40, num_shares=50, position_nav=10000.0),
        ]

        result = add_portfolio(
            positions,
            user_id=user.id,
            portfolio_name="Test Portfolio",
            portfolio_value=25000.0,
        )

        # Reason: add_portfolio returns a UUID on success
        assert result is not None
        assert user_session.add.called
        assert user_session.commit.called


class TestAddPortfolioMissingShares:
    """Tests for add_portfolio when num_shares is missing."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_add_portfolio_missing_shares_raises(self, mock_gsc):
        """Positions without num_shares raise ValueError mentioning pre-compute."""
        user = _make_mock_user()
        user_session = _make_mock_session(return_user=user)

        market_session = MagicMock()
        market_session.query.return_value = market_session
        market_session.filter.return_value = market_session
        market_session.first.return_value = MagicMock(ticker="AAPL")

        mock_gsc.side_effect = _mock_get_session_class(user_session, market_session)

        from prophitai_data.repositories.portfolio.crud import add_portfolio

        # Reason: Positions without num_shares trigger the calc removal error path
        positions = [
            _make_position("AAPL", 0.60, num_shares=None, position_nav=None),
        ]

        with pytest.raises(ValueError, match="pre-compute"):
            add_portfolio(
                positions,
                user_id=user.id,
                portfolio_name="Test Portfolio",
                portfolio_value=25000.0,
            )


class TestAddPortfolioMissingNav:
    """Tests for add_portfolio when position_nav is missing but num_shares present."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_add_portfolio_missing_nav_raises(self, mock_gsc):
        """Positions with num_shares but no position_nav raise ValueError."""
        user = _make_mock_user()
        user_session = _make_mock_session(return_user=user)

        market_session = MagicMock()
        market_session.query.return_value = market_session
        market_session.filter.return_value = market_session
        market_session.first.return_value = MagicMock(ticker="AAPL")

        mock_gsc.side_effect = _mock_get_session_class(user_session, market_session)

        from prophitai_data.repositories.portfolio.crud import add_portfolio

        positions = [
            _make_position("AAPL", 0.60, num_shares=100, position_nav=None),
        ]

        with pytest.raises(ValueError, match="pre-compute"):
            add_portfolio(
                positions,
                user_id=user.id,
                portfolio_name="Test Portfolio",
                portfolio_value=25000.0,
            )


class TestListPortfolios:
    """Tests for list_portfolios with mocked session."""

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_list_portfolios_returns_formatted(self, mock_gsc):
        """list_portfolios returns formatted list of portfolio metadata."""
        user = _make_mock_user()
        user_session = MagicMock()
        user_session.query.return_value = user_session
        user_session.filter.return_value = user_session
        user_session.first.return_value = user

        # Reason: The second .all() call returns portfolio objects
        mock_portfolio = MagicMock()
        mock_portfolio.id = uuid.uuid4()
        mock_portfolio.name = "Growth Fund"
        mock_portfolio.nav = 50000.0
        mock_portfolio.is_current = True
        mock_portfolio.is_discretionary = False
        mock_portfolio.created_date = MagicMock()
        mock_portfolio.created_date.isoformat.return_value = "2026-01-15T00:00:00"
        mock_portfolio.user_id = user.id
        user_session.all.return_value = [mock_portfolio]

        mock_gsc.side_effect = _mock_get_session_class(user_session)

        from prophitai_data.repositories.portfolio.retrieval import list_portfolios
        result = list_portfolios(email="test@example.com")

        assert len(result) == 1
        assert result[0]["name"] == "Growth Fund"
        assert result[0]["nav"] == pytest.approx(50000.0)
        assert result[0]["is_current"] is True

    @patch("prophitai_data.session.decorators._get_session_class")
    def test_list_portfolios_user_not_found(self, mock_gsc):
        """list_portfolios returns empty list when user not found."""
        user_session = _make_mock_session(return_user=None)
        mock_gsc.side_effect = _mock_get_session_class(user_session)

        from prophitai_data.repositories.portfolio.retrieval import list_portfolios
        result = list_portfolios(email="nobody@example.com")

        assert result == []
