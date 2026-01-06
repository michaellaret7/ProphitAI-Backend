import logging
from typing import List, Dict

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio, PortfolioItem
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)


class UpdatePortfolios:
    """
    Updates portfolio values based on current market prices.

    Updates in order:
    1. position_nav for each item (num_shares * current_price)
    2. portfolio nav (sum of all position_navs)
    3. allocation for each item (position_nav / portfolio_nav)
    """

    def __init__(self):
        self.session = UserSession()
        self.fmp = FMP_API_DATA()

    def _get_all_portfolios(self) -> List[Portfolio]:
        """Fetch all portfolios with their items."""
        return self.session.query(Portfolio).all()

    def _fetch_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Fetch current prices for a list of tickers."""
        if not tickers:
            return {}

        quotes = self.fmp.get_batch_quote(tickers)

        if not quotes:
            return {}

        return {
            quote["symbol"]: quote["price"]
            for quote in quotes
            if quote.get("symbol") and quote.get("price") is not None
        }

    def update_portfolios(self):
        """Update all portfolios with current market values."""
        portfolios = self._get_all_portfolios()

        for portfolio in portfolios:
            self._update_single_portfolio(portfolio)

        self.session.commit()

    def _update_single_portfolio(self, portfolio: Portfolio):
        """
        Update a single portfolio's position_navs, nav, and allocations.

        Args:
            portfolio: Portfolio object to update
        """
        items = portfolio.items
        if not items:
            logger.info(f"Portfolio {portfolio.name} has no items, skipping")
            return

        # Collect tickers that have num_shares
        tickers_with_shares = {
            item.ticker: item.num_shares
            for item in items
            if item.num_shares is not None and item.num_shares > 0
        }

        if not tickers_with_shares:
            logger.info(f"Portfolio {portfolio.name} has no positions with shares, skipping")
            return

        # Fetch current prices
        prices = self._fetch_current_prices(list(tickers_with_shares.keys()))
        if not prices:
            logger.warning(f"Could not fetch prices for portfolio {portfolio.name}")
            return

        # Step 1: Calculate and update position_nav for each item
        for item in items:
            if item.ticker in prices and item.num_shares:
                item.position_nav = item.num_shares * prices[item.ticker]
                item.updated_date = get_current_utc_time()

        # Step 2: Calculate portfolio nav as sum of position_navs
        portfolio_nav = sum(item.position_nav or 0 for item in items)
        portfolio.nav = portfolio_nav
        portfolio.updated_date = get_current_utc_time()

        # Step 3: Recalculate allocations
        if portfolio_nav > 0:
            for item in items:
                if item.position_nav is not None:
                    item.allocation = item.position_nav / portfolio_nav
                    item.updated_date = get_current_utc_time()

        logger.info(f"Updated portfolio {portfolio.name}: NAV=${portfolio_nav:,.2f}")

    def close(self):
        """Close the database session."""
        self.session.close()


