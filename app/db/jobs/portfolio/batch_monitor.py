"""
Batch portfolio monitoring with shared price data cache.

This module provides efficient batch monitoring of multiple portfolios by
fetching price data once for all unique tickers across portfolios.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio, PortfolioItem, User
from app.db.jobs.portfolio.monitor import MonitorPortfolio
from app.repositories.portfolio_data import get_all_portfolio_ids
from app.repositories.price_data import build_returns_df
from app.utils.time_utils import get_current_utc_time
from app.utils.serialize_output import serialize_sqlalchemy_obj

class BatchMonitorPortfolio:
    def __init__(self, portfolio_ids: list[str]):
        self.portfolio_ids = portfolio_ids
        self.unique_tickers = self._get_unique_tickers()
        self.oldest_portfolio_created_date = self._get_oldest_portfolio_created_date()
        self.returns_df = self._cache_returns_df(self.unique_tickers)
    
    def _get_unique_tickers(self) -> list[str]:
        with UserSession() as us:
            tickers = us.query(PortfolioItem.ticker).filter(
                PortfolioItem.portfolio_id.in_(self.portfolio_ids)
            ).distinct().all()
            return [t[0] for t in tickers]

    def _get_oldest_portfolio_created_date(self) -> datetime:
        with UserSession() as us:
            oldest_portfolio = us.query(Portfolio.created_date).filter(
                Portfolio.id.in_(self.portfolio_ids)
            ).order_by(Portfolio.created_date.asc()).first()
            return oldest_portfolio[0]
    
    def _cache_returns_df(self, tickers: list[str]) -> pd.DataFrame:
        print(f"[CACHE] Fetching returns for {len(tickers)} tickers...")

        # Reason: Ensure minimum 180 days of data for correlation detection (requires 21+ days)
        min_lookback_days = 180
        min_start_date = get_current_utc_time() - timedelta(days=min_lookback_days)

        # Use the earlier of: oldest portfolio date OR 180 days ago
        start_date = min(self.oldest_portfolio_created_date, min_start_date)

        returns_df = build_returns_df(
            tickers,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=get_current_utc_time().strftime('%Y-%m-%d'),
            frequency='daily'
        )
        print(f"[CACHE] Done. Shape: {returns_df.shape}")
        return returns_df

    def _monitor_single_portfolio(self, portfolio_id: str) -> tuple[str, Any | None]:
        """Monitor a single portfolio. Returns (portfolio_id, results) or (portfolio_id, None) on error."""
        try:
            with MonitorPortfolio(str(portfolio_id), returns_df=self.returns_df) as monitor:
                return (str(portfolio_id), monitor.notify())
        except ValueError as e:
            print(f"[SKIP] Portfolio {portfolio_id}: {e}")
            return (str(portfolio_id), None)

    def run(self, max_workers: int = 3) -> dict[str, Any]:
        """
        Run monitoring for all portfolios in parallel using cached returns data.

        Args:
            max_workers: Maximum number of concurrent threads. Keep low (≤3) to avoid
                exhausting database connection pool. Each worker uses 2 sessions
                (MonitorPortfolio) + up to 2 more for messaging = 4 connections.
                Pool limit is 15 connections.

        Returns:
            Dict mapping portfolio_id to tuple of detection results:
            (allocation_drift, drawdown, price_target_changes, correlation)
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._monitor_single_portfolio, pid): pid
                for pid in self.portfolio_ids
            }

            for future in as_completed(futures):
                portfolio_id, result = future.result()
                if result is not None:
                    results[portfolio_id] = result

        return results


if __name__ == "__main__":
    user_session = UserSession()
    portfolio_ids = user_session.query(Portfolio.id).all()
    portfolio_ids = [pid[0] for pid in portfolio_ids]
    user_session.close()

    batch_monitor = BatchMonitorPortfolio(portfolio_ids)
    results = batch_monitor.run()
    print(results)

    

