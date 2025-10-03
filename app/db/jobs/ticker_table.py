from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime
from decimal import Decimal
from sqlalchemy import update
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading

class UpdateTickerTable:
    def __init__(self):
        self.lock = threading.Lock()  # For thread-safe progress reporting
        self.total_updated = 0
        self.total_errors = 0
    
    def _retrieve_all_tickers(self):
        session = MarketSession()
        tickers = session.query(Ticker).all()
        session.close()
        return tickers

    def _retrieve_fmp_full_quote(self, ticker_symbol):
        fmp_api = FMP_API_DATA()
        ticker_data = fmp_api.get_full_quote(ticker_symbol)
        return ticker_data

    def _retrieve_fmp_company_profile(self, ticker_symbol):
        fmp_api = FMP_API_DATA()
        profile_data = fmp_api.get_company_profile(ticker_symbol)
        return profile_data
    
    def _retrieve_ticker_data(self, ticker_symbol, session):
        ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()
        return ticker
    
    def _update_single_ticker(self, ticker_data):
        """
        Thread-safe function to update a single ticker
        Each thread gets its own session for database safety
        """
        ticker_id, ticker_symbol = ticker_data
        session = MarketSession()

        try:
            # Get quote data and profile data from API
            quote_data = self._retrieve_fmp_full_quote(ticker_symbol)
            profile_data = self._retrieve_fmp_company_profile(ticker_symbol)

            if quote_data and len(quote_data) > 0:
                quote = quote_data[0]
                profile = profile_data[0] if profile_data and len(profile_data) > 0 else {}

                # Calculate dollar volume
                dollar_volume = None
                if quote.get('price') and quote.get('avgVolume'):
                    dollar_volume = Decimal(str(quote.get('price'))) * Decimal(str(quote.get('avgVolume')))

                # Parse earnings announcement datetime
                earnings_announcement = None
                if quote.get('earningsAnnouncement'):
                    try:
                        earnings_announcement = datetime.fromisoformat(quote.get('earningsAnnouncement').replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass

                # Parse IPO date
                ipo_date = None
                if profile.get('ipoDate'):
                    try:
                        ipo_date = datetime.strptime(profile.get('ipoDate'), '%Y-%m-%d').date()
                    except (ValueError, AttributeError):
                        pass

                # Prepare update values
                update_values = {
                    'price': quote.get('price'),
                    'market_cap': Decimal(str(quote.get('marketCap', 0))) if quote.get('marketCap') else None,
                    'avg_volume': Decimal(str(quote.get('avgVolume', 0))) if quote.get('avgVolume') else None,
                    'eps': quote.get('eps'),
                    'pe': quote.get('pe'),
                    'dollar_volume': dollar_volume,
                    'last_updated': datetime.now(),
                    'beta': profile.get('beta'),
                    'is_actively_trading': profile.get('isActivelyTrading'),
                    'is_adr': profile.get('isAdr'),
                    'is_fund': profile.get('isFund'),
                    'ipo_date': ipo_date,
                    'earnings_announcement': earnings_announcement,
                    'shares_outstanding': Decimal(str(quote.get('sharesOutstanding', 0))) if quote.get('sharesOutstanding') else None
                }

                # Bulk update using session.execute()
                session.execute(
                    update(Ticker).where(Ticker.id == ticker_id).values(**update_values)
                )

                session.commit()

                # Thread-safe progress reporting
                with self.lock:
                    self.total_updated += 1

                return ticker_symbol, True, "Success"
            else:
                return ticker_symbol, False, "No quote data"

        except Exception as e:
            session.rollback()
            with self.lock:
                self.total_errors += 1
            return ticker_symbol, False, f"Error: {str(e)}"
        finally:
            session.close()
    
    def run_update_parallel(self, max_workers=5):
        """
        Parallel update using ThreadPoolExecutor
        Each thread handles its own API call and database update
        """
        # Get ticker IDs and symbols only to minimize memory usage
        session = MarketSession()
        try:
            ticker_data = session.query(Ticker.id, Ticker.ticker).all()
            total_tickers = len(ticker_data)
        finally:
            session.close()

        try:
            print(f"Starting parallel update of {total_tickers} tickers with {max_workers} workers...")
            start_time = time.time()

            # Reset counters
            self.total_updated = 0
            self.total_errors = 0

            results = []

            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_ticker = {
                    executor.submit(self._update_single_ticker, ticker): ticker[1]
                    for ticker in ticker_data
                }

                # Process completed tasks
                for future in as_completed(future_to_ticker):
                    ticker_symbol = future_to_ticker[future]
                    try:
                        result = future.result()
                        results.append(result)

                        # Progress report every 100 completed tickers
                        if len(results) % 100 == 0:
                            with self.lock:
                                print(f"Progress: {len(results)}/{total_tickers} - Updated: {self.total_updated}, Errors: {self.total_errors}")
                    except Exception as exc:
                        print(f"Ticker {ticker_symbol} generated an exception: {exc}")
                        results.append((ticker_symbol, False, f"Exception: {exc}"))
                        with self.lock:
                            self.total_errors += 1

            # Final summary
            end_time = time.time()
            duration = end_time - start_time

            print(f"\n{'='*60}")
            print("PARALLEL UPDATE SUMMARY:")
            print(f"Total tickers processed: {len(results)}")
            print(f"Successfully updated: {self.total_updated}")
            print(f"Failed updates: {self.total_errors}")
            print(f"Time taken: {duration:.2f} seconds")
            print(f"Average time per ticker: {duration/len(results):.3f} seconds")
            print(f"Throughput: {len(results)/duration:.2f} tickers/second")
            print("="*60)

            return results

        except Exception as e:
            print(f"Parallel update failed: {e}")
            raise


if __name__ == "__main__":
    update_ticker_table = UpdateTickerTable()
    update_ticker_table.run_update_parallel()









