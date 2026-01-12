import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio, PortfolioItem
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)

# Reason: FMP API batch quote limit per request
MAX_TICKERS_PER_BATCH = 100
# Reason: Balance between parallelism and resource usage
MAX_WORKERS = 4

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

    def _fetch_all_prices_parallel(self, all_tickers: List[str]) -> Dict[str, float]:
        """
        Fetch prices for all tickers using parallel batch requests.

        Splits tickers into batches and fetches them concurrently.
        """
        if not all_tickers:
            return {}

        unique_tickers = list(set(all_tickers))

        # Reason: Single batch - no need for parallelism
        if len(unique_tickers) <= MAX_TICKERS_PER_BATCH:
            return self._fetch_current_prices(unique_tickers)

        # Split into batches
        batches = [
            unique_tickers[i : i + MAX_TICKERS_PER_BATCH]
            for i in range(0, len(unique_tickers), MAX_TICKERS_PER_BATCH)
        ]

        all_prices: Dict[str, float] = {}

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_current_prices, batch): batch
                for batch in batches
            }

            for future in as_completed(futures):
                batch = futures[future]
                try:
                    prices = future.result()
                    all_prices.update(prices)
                except Exception as e:
                    logger.error(f"Failed to fetch batch {batch[:3]}...: {e}")

        return all_prices

    def update_portfolios(self):
        """
        Update all portfolios with current market values.

        Optimization:
        1. Fetches all prices upfront in parallel batches
        2. Computes all updates in memory
        3. Bulk writes to DB in minimal round-trips
        """
        portfolios = self._get_all_portfolios()
        if not portfolios:
            logger.info("No portfolios to update")
            return

        # Reason: Collect ALL tickers upfront to minimize API calls
        all_tickers = []
        for portfolio in portfolios:
            all_tickers.extend(item.ticker for item in portfolio.items)

        if not all_tickers:
            logger.info("No tickers across all portfolios")
            return

        # Fetch all prices once (parallelized if > MAX_TICKERS_PER_BATCH)
        logger.info(f"Fetching prices for {len(set(all_tickers))} unique tickers")
        prices = self._fetch_all_prices_parallel(all_tickers)

        if not prices:
            logger.warning("Could not fetch any prices")
            return

        # Compute all updates in memory, then bulk write
        portfolio_updates: List[Dict] = []
        item_updates: List[Dict] = []
        now = get_current_utc_time()

        for portfolio in portfolios:
            portfolio_update, items_update = self._compute_portfolio_updates(
                portfolio, prices, now
            )
            if portfolio_update:
                portfolio_updates.append(portfolio_update)
            item_updates.extend(items_update)

        # Bulk update in minimal DB round-trips
        if item_updates:
            self.session.bulk_update_mappings(PortfolioItem, item_updates)
        if portfolio_updates:
            self.session.bulk_update_mappings(Portfolio, portfolio_updates)

        self.session.commit()
        logger.info(
            f"Bulk updated {len(portfolio_updates)} portfolios, "
            f"{len(item_updates)} items"
        )

    def _compute_portfolio_updates(
        self, portfolio: Portfolio, prices: Dict[str, float], now
    ) -> tuple[Dict | None, List[Dict]]:
        """
        Compute updates for a portfolio without modifying ORM objects.

        Returns dicts suitable for bulk_update_mappings.

        Args:
            portfolio: Portfolio object to compute updates for
            prices: Pre-fetched price cache (ticker -> price)
            now: Current UTC timestamp

        Returns:
            Tuple of (portfolio_update_dict, list_of_item_update_dicts)
        """
        items = portfolio.items
        if not items:
            logger.info(f"Portfolio {portfolio.name} has no items, skipping")
            return None, []

        item_updates: List[Dict] = []
        # Reason: Composite PK is (portfolio_id, ticker)
        item_position_navs: Dict[str, float] = {}  # ticker -> position_nav

        # Step 1: Calculate num_shares if missing
        for item in items:
            # Reason: PortfolioItem uses composite PK (portfolio_id, ticker)
            update = {"portfolio_id": item.portfolio_id, "ticker": item.ticker}
            has_changes = False

            if (
                item.num_shares is None
                and item.allocation
                and item.ticker in prices
                and portfolio.nav
                and portfolio.nav > 0
            ):
                target_value = item.allocation * portfolio.nav
                update["num_shares"] = int(target_value / prices[item.ticker])
                has_changes = True
                logger.info(
                    f"Calculated num_shares for {item.ticker}: {update['num_shares']}"
                )

            # Step 2: Calculate position_nav
            num_shares = update.get("num_shares", item.num_shares)
            if item.ticker in prices and num_shares:
                position_nav = num_shares * prices[item.ticker]
                update["position_nav"] = position_nav
                item_position_navs[item.ticker] = position_nav
                has_changes = True
            else:
                # Keep existing position_nav for portfolio sum
                item_position_navs[item.ticker] = item.position_nav or 0

            if has_changes:
                update["updated_date"] = now
                item_updates.append(update)

        # Step 3: Calculate portfolio nav
        portfolio_nav = sum(item_position_navs.values())

        # Step 4: Calculate allocations
        if portfolio_nav > 0:
            for update in item_updates:
                ticker = update["ticker"]
                if ticker in item_position_navs:
                    update["allocation"] = item_position_navs[ticker] / portfolio_nav

        portfolio_update = {
            "id": portfolio.id,
            "nav": portfolio_nav,
            "updated_date": now,
        }

        logger.info(f"Computed updates for {portfolio.name}: NAV=${portfolio_nav:,.2f}")
        return portfolio_update, item_updates

    def close(self):
        """Close the database session."""
        self.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_portfolios = UpdatePortfolios()
    update_portfolios.update_portfolios()
    update_portfolios.close()