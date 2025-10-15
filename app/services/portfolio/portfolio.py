from typing import Dict, Any, List, Tuple, Optional
import uuid
from app.repositories.portfolio_data import (
    add_portfolio,
    update_portfolio,
    delete_portfolio,
    list_portfolios,
    retrieve_portfolio
)
from app.repositories.user_data import get_all_user_data, get_user_basic_info


class Position:
    """Simple position object for portfolio creation."""
    def __init__(self, ticker: str, allocation: float):
        self.ticker = ticker
        self.allocation = allocation


class PortfolioService:
    """
    Service for portfolio CRUD operations and list management.

    Handles portfolio creation, updates, deletion, and retrieval.
    Eliminates duplication by providing shared helper methods for
    building portfolio list responses.
    """

    def create_portfolio(
        self,
        *,
        email: str,
        company_name: str,
        portfolio_name: str,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a new portfolio for a user.

        Args:
            email: User's email address
            company_name: Company name for the portfolio
            portfolio_name: Name of the portfolio
            positions: List of dicts with 'ticker' and 'allocation' keys

        Returns:
            Dict containing user_data and portfolios for response building

        Raises:
            ValueError: If validation fails
        """
        if not email:
            raise ValueError("Email is required")
        if not company_name:
            raise ValueError("Company name is required")
        if not portfolio_name:
            raise ValueError("Portfolio name is required")
        if not positions or not isinstance(positions, list):
            raise ValueError("Positions must be a non-empty list")

        # Transform positions to Position objects
        position_objs = []
        for p in positions:
            ticker = p.get("ticker")
            allocation = p.get("allocation")
            if ticker is None or allocation is None:
                raise ValueError("Each position requires ticker and allocation")
            position_objs.append(Position(ticker=ticker, allocation=allocation))

        # Create portfolio in database
        add_portfolio(
            portfolio=position_objs,
            company_name=company_name,
            user_email=email,
            portfolio_name=portfolio_name,
        )

        # Return updated portfolio list data
        return self._get_portfolio_list_data(email)

    def update_portfolio(
        self,
        *,
        email: str,
        portfolio_id: str,
        name: Optional[str] = None,
        is_current: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing portfolio.

        Args:
            email: User's email address
            portfolio_id: UUID of the portfolio to update
            name: Optional new name for the portfolio
            is_current: Optional flag to set as current portfolio

        Returns:
            Dict containing user_data and portfolios for response building

        Raises:
            ValueError: If validation fails or portfolio not found
        """
        if not email:
            raise ValueError("Email is required")
        if not portfolio_id:
            raise ValueError("portfolioId is required")

        # Update portfolio in database
        updated = update_portfolio(
            email=email,
            portfolio_id=uuid.UUID(portfolio_id),
            name=name,
            is_current=is_current,
        )

        if not updated:
            raise ValueError("Portfolio not found")

        # Return updated portfolio list data
        return self._get_portfolio_list_data(email)

    def delete_portfolio(
        self,
        *,
        email: str,
        portfolio_id: str
    ) -> Dict[str, Any]:
        """
        Delete a portfolio.

        Args:
            email: User's email address
            portfolio_id: UUID of the portfolio to delete

        Returns:
            Dict containing user_data and portfolios for response building

        Raises:
            ValueError: If validation fails or portfolio not found
        """
        if not email:
            raise ValueError("Email is required")
        if not portfolio_id:
            raise ValueError("portfolioId is required")

        # Delete portfolio from database
        deleted = delete_portfolio(
            email=email,
            portfolio_id=uuid.UUID(portfolio_id),
        )

        if not deleted:
            raise ValueError("Portfolio not found")

        # Return updated portfolio list data
        return self._get_portfolio_list_data(email)

    def get_user_portfolios(self, email: str) -> Dict[str, Any]:
        """
        Get all portfolios for a user.

        Args:
            email: User's email address

        Returns:
            Dict containing user_data and portfolios for response building

        Raises:
            ValueError: If user not found
        """
        if not email:
            raise ValueError("Email is required")

        return self._get_portfolio_list_data(email)

    def get_portfolio_positions(self, portfolio_id: str, email: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get positions for a specific portfolio.

        Args:
            portfolio_id: UUID of the portfolio
            email: Optional email for additional validation

        Returns:
            List of position dictionaries

        Raises:
            ValueError: If portfolio not found
        """
        if not portfolio_id:
            raise ValueError("portfolioId is required")

        positions = retrieve_portfolio(
            email=email,
            portfolio_id=uuid.UUID(portfolio_id)
        )

        if not positions:
            raise ValueError("Portfolio not found")

        return positions

    def _get_portfolio_list_data(self, email: str) -> Dict[str, Any]:
        """
        Helper method to get user data and formatted portfolio list.

        This eliminates the 80+ lines of duplication across create/update/delete
        operations by centralizing the portfolio list retrieval and formatting.

        Args:
            email: User's email address

        Returns:
            Dict with 'user_data', 'portfolios', and 'counts' keys

        Raises:
            ValueError: If user not found
        """
        # Get user data
        user_data = get_all_user_data(email=email)
        if not user_data:
            raise ValueError("User not found")

        # Get and format portfolios
        portfolios = user_data.get('portfolios', [])
        portfolios_formatted = [{
            "name": p.get("name"),
            "portfolioId": p.get("portfolio_id"),
            "isCurrent": p.get("is_current")
        } for p in portfolios]

        # Build counts metadata
        counts = {
            'currentItemCount': len(portfolios_formatted),
            'itemsPerPage': len(portfolios_formatted),
            'startIndex': 1,
            'totalItems': len(portfolios_formatted),
        }

        return {
            'user_data': user_data,
            'portfolios': portfolios_formatted,
            'counts': counts,
            'email': email
        }
