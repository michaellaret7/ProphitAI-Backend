"""
Fundamentals Update Orchestrator

Orchestrates parallel updates of all fundamental data types for tickers.
Combines FinancialStatementsUpdater, AnalystDataUpdater, NewsDataUpdater,
and ETFDataUpdater into a single coordinated update process.

Usage:
    updater = FundamentalsUpdater()
    updater.update_all_fundamentals(max_workers=5)
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.db.jobs.fundamentals.financial_statements import FinancialStatementsUpdater
from app.db.jobs.fundamentals.analyst_data import AnalystDataUpdater
from app.db.jobs.fundamentals.news_data import NewsDataUpdater
from app.db.jobs.fundamentals.etf_data import ETFDataUpdater


class FundamentalsUpdater:
    """
    Orchestrates parallel updates of all fundamental data for tickers.

    Combines all sub-updaters (financial statements, analyst data, news, ETF)
    into a coordinated parallel processing workflow with progress tracking.
    """

    def __init__(self):
        self.lock = threading.Lock()

        # Progress tracking counters
        self.total_tickers = 0
        self.processed = 0
        self.errors = 0

        # Data type specific counters
        self.counters = {
            'balance_sheets': 0,
            'cash_flows': 0,
            'income_statements': 0,
            'financial_ratios': 0,
            'analyst_estimates': 0,
            'stock_grades': 0,
            'rating_scores': 0,
            'analyst_recommendations': 0,
            'price_targets': 0,
            'etf_holdings': 0,
            'etf_info': 0,
            'dividends': 0,
            'press_releases': 0,
            'stock_news': 0,
            'price_target_news': 0,
            'stock_grade_news': 0,
            'earnings_transcripts': 0
        }

        # Initialize sub-updaters
        self._financial_updater = FinancialStatementsUpdater()
        self._analyst_updater = AnalystDataUpdater()
        self._news_updater = NewsDataUpdater()
        self._etf_updater = ETFDataUpdater()

    def _reset_counters(self) -> None:
        """Reset all progress counters."""
        self.processed = 0
        self.errors = 0
        self.counters = {k: 0 for k in self.counters}

    def _update_single_ticker_fundamentals(
        self,
        ticker_data: Tuple[str, str]
    ) -> Dict[str, Any]:
        """
        Update all fundamental data for a single ticker (thread-safe).

        Args:
            ticker_data: Tuple of (ticker_id, ticker_symbol)

        Returns:
            Dictionary with ticker, success status, and update details
        """
        ticker_id, ticker_symbol = ticker_data
        session = MarketSession()
        fmp_api = FMP_API_DATA()

        results = {
            'ticker': ticker_symbol,
            'success': True,
            'details': {}
        }

        try:
            # Define all update operations with their data types and methods
            update_operations = [
                # Financial Statements
                ('balance_sheets', self._financial_updater.update_balance_sheets),
                ('cash_flows', self._financial_updater.update_cash_flows),
                ('income_statements', self._financial_updater.update_income_statements),
                ('financial_ratios', self._financial_updater.update_financial_ratios),
                # Analyst Data
                ('analyst_estimates', self._analyst_updater.update_analyst_estimates),
                ('stock_grades', self._analyst_updater.update_stock_grades),
                ('rating_scores', self._analyst_updater.update_rating_scores),
                ('analyst_recommendations', self._analyst_updater.update_analyst_recommendations),
                ('price_targets', self._analyst_updater.update_price_target_summary),
                # ETF Data
                ('etf_holdings', self._etf_updater.update_etf_holdings),
                ('etf_info', self._etf_updater.update_etf_info),
                ('dividends', self._etf_updater.update_dividends),
                # News Data
                ('press_releases', self._news_updater.update_press_releases),
                ('stock_news', self._news_updater.update_stock_news),
                ('price_target_news', self._news_updater.update_price_target_news),
                ('stock_grade_news', self._news_updater.update_stock_grade_news),
                ('earnings_transcripts', self._news_updater.update_earnings_transcripts),
            ]

            for data_type, update_method in update_operations:
                try:
                    # Create a savepoint before each update method
                    session.execute(text(f"SAVEPOINT sp_{data_type}"))

                    count = update_method(ticker_id, ticker_symbol, session, fmp_api)
                    results['details'][data_type] = count

                    # If successful, release the savepoint
                    session.execute(text(f"RELEASE SAVEPOINT sp_{data_type}"))

                    # Update counters
                    with self.lock:
                        if count > 0:
                            self.counters[data_type] += count
                        elif count == -1:
                            results['success'] = False

                except Exception as e:
                    # Rollback to the savepoint if this specific update fails
                    session.execute(text(f"ROLLBACK TO SAVEPOINT sp_{data_type}"))
                    print(f"Failed to update {data_type} for {ticker_symbol}: {str(e)}")
                    results['details'][data_type] = -1

            # Commit all successful changes for this ticker
            session.commit()

            # Update progress
            with self.lock:
                self.processed += 1
                if self.processed % 10 == 0:
                    print(f"Progress: {self.processed}/{self.total_tickers} tickers processed")

            return results

        except Exception as e:
            session.rollback()
            print(f"Error updating fundamentals for {ticker_symbol}: {str(e)}")
            results['success'] = False
            results['error'] = str(e)

            with self.lock:
                self.errors += 1

            return results

        finally:
            session.close()

    def update_all_fundamentals(
        self,
        max_workers: int = 5,
        ticker_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Update fundamental data for all tickers using parallel processing.

        Args:
            max_workers: Number of parallel threads to use
            ticker_limit: Optional limit on number of tickers to process

        Returns:
            List of result dictionaries for each ticker
        """
        session = MarketSession()

        try:
            # Get all tickers
            query = session.query(Ticker.id, Ticker.ticker)
            if ticker_limit:
                query = query.limit(ticker_limit)

            ticker_data = query.all()
            self.total_tickers = len(ticker_data)

            # Reset counters
            self._reset_counters()

            print(f"Starting fundamental data update for {self.total_tickers} "
                  f"tickers with {max_workers} workers...")
            start_time = time.time()

            results = []

            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_ticker = {
                    executor.submit(self._update_single_ticker_fundamentals, ticker): ticker[1]
                    for ticker in ticker_data
                }

                # Process completed tasks
                for future in as_completed(future_to_ticker):
                    ticker_symbol = future_to_ticker[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as exc:
                        print(f"Ticker {ticker_symbol} generated an exception: {exc}")
                        results.append({
                            'ticker': ticker_symbol,
                            'success': False,
                            'error': str(exc)
                        })

            # Final summary
            end_time = time.time()
            duration = end_time - start_time

            self._print_summary(duration, results)

            return results

        except Exception as e:
            print(f"Fundamental data update failed: {e}")
            raise
        finally:
            try:
                session.close()
            except Exception as e:
                print(f"Warning: Error closing session (data was saved successfully): {e}")

    def _print_summary(self, duration: float, results: List[Dict[str, Any]]) -> None:
        """Print a detailed summary of the update process."""
        successful = sum(1 for r in results if r['success'])

        print(f"\n{'='*70}")
        print("FUNDAMENTAL DATA UPDATE SUMMARY:")
        print(f"{'='*70}")
        print(f"Total tickers processed: {len(results)}")
        print(f"Successful updates: {successful}")
        print(f"Failed updates: {self.errors}")
        print(f"Time taken: {duration:.2f} seconds")
        if results:
            print(f"Average time per ticker: {duration/len(results):.3f} seconds")
        print(f"\nRecords updated by type:")
        for data_type, count in self.counters.items():
            if count > 0:
                print(f"  {data_type}: {count:,}")
        print("="*70)


# Backwards compatibility alias
UpdateFundamentalData = FundamentalsUpdater


if __name__ == "__main__":
    updater = FundamentalsUpdater()
    updater.update_all_fundamentals(max_workers=5)
