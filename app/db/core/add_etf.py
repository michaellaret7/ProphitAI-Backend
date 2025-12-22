from app.repositories.price_data import get_price_data_15_mins
from app.db.core.db_config import MarketSession, market_engine
from app.db.core.models.market_data_models import (
    Ticker, Price, DailyPrices, ETFInfo, ETFHolding, Dividend
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.db.core.db_utils import bulk_insert_with_copy
from datetime import datetime, timedelta, timezone
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
import pandas as pd
import time
import uuid


class OptimizedETFDataLoader:
    """
    Optimized ETF data loader with better performance for price data fetching.
    
    Key improvements:
    - Configurable date range (default 2 years instead of 6)
    - Larger data chunks for fewer API calls
    - Option to fetch daily data for initial loading
    - Better progress tracking
    - All timestamps stored in UTC for consistency
    """
    def __init__(self, ticker, sector=None, industry=None, sub_industry=None, years_of_history=2):
        self.ticker = ticker.upper()
        self.sector = sector
        self.industry = industry
        self.sub_industry = sub_industry
        self.years_of_history = years_of_history  # Configurable history range
        self.fmp_api = FMP_API_DATA()
        self.ticker_id = None
        self.session = None
        
    def _ensure_ticker_exists(self, allow_partial_reload=False):
        """
        Check if ticker exists in database. 
        Returns True if ticker is new, False if it already exists.
        If allow_partial_reload is True, continues with existing ticker to complete missing data.
        """
        ticker_obj = self.session.query(Ticker).filter(Ticker.ticker == self.ticker).first()
        
        if ticker_obj:
            self.ticker_id = ticker_obj.id
            print(f"[{self.ticker}] ⚠️ Ticker already exists in database.")
            
            # Check existing data completeness
            price_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
            etf_info_exists = self.session.query(ETFInfo).filter(ETFInfo.ticker_id == self.ticker_id).first() is not None
            holdings_count = self.session.query(ETFHolding).filter(ETFHolding.ticker_id == self.ticker_id).count()
            
            print(f"[{self.ticker}] ℹ️ Existing data status:")
            print(f"  - Price records: {price_count:,}")
            print(f"  - ETF info: {'Yes' if etf_info_exists else 'No'}")
            print(f"  - Holdings: {holdings_count}")
            
            if allow_partial_reload:
                print(f"[{self.ticker}] 🔄 Continuing to complete partial data...")
                return "partial"  # Special return value to indicate partial reload
            
            return False
        
        # Create new ticker entry
        print(f"[{self.ticker}] Creating new ticker entry...")
        if self.sector or self.industry or self.sub_industry:
            print(f"[{self.ticker}] Classification - Sector: {self.sector or 'None'}, Industry: {self.industry or 'None'}, Sub-Industry: {self.sub_industry or 'None'}")
        
        ticker_obj = Ticker(
            id=uuid.uuid4(),
            ticker=self.ticker,
            is_etf=True,
            sector=self.sector,
            industry=self.industry,
            sub_industry=self.sub_industry
        )
        self.session.add(ticker_obj)
        self.session.flush()
        
        self.ticker_id = ticker_obj.id
        return True
    
    def _update_ticker_quote_data(self):
        """Update ticker table with latest quote data."""
        print(f"[{self.ticker}] Fetching quote data...")
        quote_data = self.fmp_api.get_full_quote(self.ticker)
        
        if quote_data and len(quote_data) > 0:
            quote = quote_data[0]
            
            update_data = {
                'price': quote.get('price'),
                'market_cap': quote.get('marketCap'),
                'avg_volume': quote.get('avgVolume'),
                'eps': quote.get('eps'),
                'pe': quote.get('pe'),
                'dollar_volume': quote.get('avgVolume', 0) * quote.get('price', 0) if quote.get('avgVolume') and quote.get('price') else None,
                'last_updated': datetime.now(timezone.utc)
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            if update_data:
                self.session.query(Ticker).filter(Ticker.id == self.ticker_id).update(update_data)
                self.session.flush()
                print(f"[{self.ticker}] ✅ Updated quote data")
    
    def _load_price_data_optimized(self):
        """
        Optimized price data loading with fewer API calls.
        Uses monthly chunks instead of 2-week chunks.
        """
        print(f"[{self.ticker}] Loading price data (optimized)...")
        
        # Check if price data already exists
        existing_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
        if existing_count > 0:
            print(f"[{self.ticker}] 🐬 {existing_count:,} price records already exist")
            return True
        
        # Try fetching from repository first (uses existing data if available)
        start_date = datetime.now(timezone.utc) - timedelta(days=365 * self.years_of_history)
        end_date = datetime.now(timezone.utc)
        
        try:
            print(f"[{self.ticker}] Attempting to fetch {self.years_of_history} years of data...")
            price_data = get_price_data_15_mins(self.ticker, start_date, end_date)
            
            if price_data.empty:
                print(f"[{self.ticker}] No existing data, fetching from FMP API...")
                price_data = self._get_intraday_prices_optimized()
            
            if not price_data.empty:
                # Format data for insertion
                price_data['ticker_id'] = self.ticker_id
                price_data.rename(columns={'date': 'datetime'}, inplace=True)
                
                for col in ['open', 'high', 'low', 'close']:
                    price_data[col] = pd.to_numeric(price_data[col], errors='coerce')
                
                price_data['volume'] = pd.to_numeric(price_data['volume'], errors='coerce').fillna(0).astype(int)
                
                # Convert to list of dicts
                price_records = price_data.to_dict('records')
                
                # Bulk insert using COPY
                ordered_columns = ['ticker_id', 'datetime', 'open', 'high', 'low', 'close', 'volume']
                bulk_insert_with_copy(self.session, Price.__table__.fullname, price_records, ordered_columns)
                
                print(f"[{self.ticker}] ✅ Loaded {len(price_records):,} price records")
                return True
            else:
                print(f"[{self.ticker}] ❌ No price data found")
                return False
                
        except Exception as e:
            print(f"[{self.ticker}] ❌ Error loading price data: {e}")
            return False
    
    def _get_intraday_prices_optimized(self):
        """
        Optimized intraday price fetching with monthly chunks.
        Reduces API calls from ~156 to ~24 for 2 years of data.
        """
        all_data = []
        to_date = datetime.now(timezone.utc)
        limit_date = datetime.now(timezone.utc) - timedelta(days=365 * self.years_of_history)
        call_count = 0
        
        print(f"[{self.ticker}] Fetching {self.years_of_history} years of intraday data...")
        print(f"[{self.ticker}] Date range: {limit_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
        
        # Use monthly chunks instead of 2-week chunks
        while to_date > limit_date:
            call_count += 1
            from_date = to_date - timedelta(days=30)  # Monthly chunks
            if from_date < limit_date:
                from_date = limit_date
            
            print(f"[{self.ticker}] API call #{call_count}: Fetching {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
            
            try:
                price_chunk = self.fmp_api.get_intraday_prices_for_ticker(
                    ticker=self.ticker,
                    from_date=from_date,
                    to_date=to_date
                )
                
                if not price_chunk:
                    print(f"[{self.ticker}] No data for this period")
                    # Try to continue with next chunk instead of stopping
                    to_date = from_date
                    continue
                
                all_data.extend(price_chunk)
                print(f"[{self.ticker}] Received {len(price_chunk):,} records. Total: {len(all_data):,}")
                
                # Move to next chunk
                to_date = from_date
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[{self.ticker}] Error fetching chunk: {e}")
                # Continue with next chunk
                to_date = from_date
        
        if not all_data:
            return pd.DataFrame()
        
        print(f"[{self.ticker}] Processing {len(all_data):,} total records...")
        df = pd.DataFrame(all_data)
        df.drop_duplicates(subset=['date'], inplace=True)
        # Ensure datetime is in UTC
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df.sort_values(by='date', inplace=True)
        
        print(f"[{self.ticker}] After deduplication: {len(df):,} records")
        return df

    def _load_daily_prices(self):
        """Load daily OHLCV data into DailyPrices table."""
        print(f"[{self.ticker}] Loading daily prices...")

        # Check if daily price data already exists
        existing_count = self.session.query(DailyPrices).filter(
            DailyPrices.ticker_id == self.ticker_id
        ).count()

        if existing_count > 0:
            print(f"[{self.ticker}] 🐬 {existing_count:,} daily price records already exist")
            return True

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365 * self.years_of_history)

        try:
            print(f"[{self.ticker}] Fetching daily prices from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")

            daily_data = self.fmp_api.get_daily_prices_for_ticker(
                self.ticker,
                start_date,
                end_date
            )

            if not daily_data or 'historical' not in daily_data or not daily_data['historical']:
                print(f"[{self.ticker}] ⚠️ No daily price data found from API")
                return False

            # Build records for insertion
            daily_records = []
            for day_data in daily_data['historical']:
                date_str = day_data.get('date')
                if not date_str:
                    continue

                # Parse the date - store as datetime at midnight for consistency
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                daily_records.append({
                    'ticker_id': self.ticker_id,
                    'datetime': date_obj,
                    'open': day_data.get('open'),
                    'high': day_data.get('high'),
                    'low': day_data.get('low'),
                    'close': day_data.get('close'),
                    'adj_close': day_data.get('adjClose'),
                    'volume': day_data.get('volume')
                })

            if not daily_records:
                print(f"[{self.ticker}] ⚠️ No valid daily price records to insert")
                return False

            # Bulk insert with conflict handling
            stmt = insert(DailyPrices).values(daily_records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['ticker_id', 'datetime'])
            result = self.session.execute(stmt)
            self.session.flush()

            print(f"[{self.ticker}] ✅ Loaded {len(daily_records):,} daily price records")
            return True

        except Exception as e:
            print(f"[{self.ticker}] ❌ Error loading daily prices: {e}")
            return False

    def _load_etf_info(self):
        """Load ETF metadata into etf_info table."""
        print(f"[{self.ticker}] Loading ETF info...")
        
        # Check if info already exists
        existing_info = self.session.query(ETFInfo).filter(ETFInfo.ticker_id == self.ticker_id).first()
        
        etf_info_data = self.fmp_api.get_etf_info(self.ticker)
        
        if etf_info_data and len(etf_info_data) > 0:
            info = etf_info_data[0]
            
            info_record = {
                'ticker_id': self.ticker_id,
                'name': info.get('name'),
                'description': info.get('description'),
                'isin': info.get('isin'),
                'assetClass': info.get('assetClass'),
                'securityCusip': info.get('cusip'),
                'domicile': info.get('domicile'),
                'website': info.get('website'),
                'etfCompany': info.get('etfCompany'),
                'expenseRatio': info.get('expenseRatio'),
                'assetsUnderManagement': info.get('aum'),
                'avgVolume': info.get('avgVolume'),
                'inceptionDate': pd.to_datetime(info.get('inceptionDate'), utc=True) if info.get('inceptionDate') else None,
                'nav': info.get('nav'),
                'navCurrency': info.get('navCurrency'),
                'holdingsCount': info.get('holdingsCount'),
                'updatedAt': datetime.now(timezone.utc),
                'sectorsList': info.get('sectorsList')
            }
            
            # Remove None values
            info_record = {k: v for k, v in info_record.items() if v is not None}
            
            if existing_info:
                # Update existing record
                for key, value in info_record.items():
                    if key != 'ticker_id':
                        setattr(existing_info, key, value)
                print(f"[{self.ticker}] ✅ Updated ETF info")
            else:
                # Create new record
                etf_info_obj = ETFInfo(**info_record)
                self.session.add(etf_info_obj)
                print(f"[{self.ticker}] ✅ Created ETF info")
            
            self.session.flush()
        else:
            print(f"[{self.ticker}] ⚠️ No ETF info data found")
    
    def _load_etf_holdings(self):
        """Load ETF holdings data."""
        print(f"[{self.ticker}] Loading ETF holdings...")

        # Check for existing holdings first and get their assets
        existing_holdings = self.session.query(ETFHolding).filter(ETFHolding.ticker_id == self.ticker_id).all()
        existing_assets = set()

        if existing_holdings:
            print(f"[{self.ticker}] Found {len(existing_holdings)} existing holdings")
            existing_assets = {h.asset for h in existing_holdings}
            print(f"[{self.ticker}] Existing assets: {', '.join(list(existing_assets)[:5])}{'...' if len(existing_assets) > 5 else ''}")

            # Try to delete existing holdings
            try:
                deleted_count = self.session.query(ETFHolding).filter(ETFHolding.ticker_id == self.ticker_id).delete()
                self.session.flush()  # Flush but don't commit - stay in transaction
                print(f"[{self.ticker}] Removed {deleted_count} existing holdings (pending commit)")
            except Exception as e:
                print(f"[{self.ticker}] Warning: Could not delete existing holdings: {e}")
                print(f"[{self.ticker}] Will skip duplicate assets during insertion")
        
        holdings_data = self.fmp_api.get_etf_holdings(self.ticker)

        if holdings_data:
            holdings_records = []
            skipped_duplicates = []
            duplicate_count = 0  # Track how many duplicates we handled
            seen_assets = set()  # Track assets we've already processed in this batch

            for holding in holdings_data:
                # Get asset and clean it (remove extra whitespace)
                asset = (holding.get('asset', '') or '').strip()

                # Skip if no asset identifier or empty after stripping
                if not asset:
                    continue

                # Check for duplicate assets in existing data (in case deletion failed)
                if existing_assets and asset in existing_assets:
                    skipped_duplicates.append(asset)
                    continue

                # Handle duplicates in the current batch
                # If we've seen this asset already, make it unique by appending the name + counter
                if asset in seen_assets:
                    duplicate_count += 1
                    name = holding.get('name', '')
                    if name:
                        # Create a unique identifier by combining asset and part of the name
                        name_suffix = name.replace(' ', '_').replace('/', '_')[:20]
                        unique_asset = f"{asset}_{name_suffix}"

                        # If still a duplicate, append a counter until unique
                        counter = 1
                        base_asset = unique_asset
                        while unique_asset in seen_assets:
                            counter += 1
                            unique_asset = f"{base_asset}_{counter}"

                        asset = unique_asset
                    else:
                        # No name to distinguish - use counter only
                        counter = 1
                        base_asset = asset
                        unique_asset = f"{asset}_{counter}"
                        while unique_asset in seen_assets:
                            counter += 1
                            unique_asset = f"{base_asset}_{counter}"
                        asset = unique_asset

                seen_assets.add(asset)

                holding_record = {
                    'ticker_id': self.ticker_id,
                    'asset': asset,
                    'name': holding.get('name'),
                    'isin': holding.get('isin'),
                    'securityCusip': holding.get('cusip'),  # camelCase to match database
                    'sharesNumber': holding.get('sharesNumber'),  # camelCase to match database
                    'weightPercentage': holding.get('weightPercentage'),  # camelCase to match database
                    'marketValue': holding.get('marketValue'),  # camelCase to match database
                    'updatedAt': datetime.now(timezone.utc)  # camelCase to match database, using UTC
                }

                holdings_records.append(holding_record)

            if duplicate_count > 0:
                print(f"[{self.ticker}] ℹ️ Renamed {duplicate_count} duplicate assets to unique identifiers")

            if skipped_duplicates:
                print(f"[{self.ticker}] ⚠️ Skipped {len(skipped_duplicates)} duplicate assets: {', '.join(skipped_duplicates[:5])}{'...' if len(skipped_duplicates) > 5 else ''}")

            if holdings_records:
                try:
                    # Bulk insert holdings - using camelCase to match database columns
                    ordered_columns = ['ticker_id', 'asset', 'name', 'isin', 'securityCusip',
                                     'sharesNumber', 'weightPercentage', 'marketValue', 'updatedAt']
                    bulk_insert_with_copy(self.session, ETFHolding.__table__.fullname, holdings_records, ordered_columns)

                    print(f"[{self.ticker}] ✅ Loaded {len(holdings_records)} holdings")
                except Exception as e:
                    print(f"[{self.ticker}] ❌ Error inserting holdings: {e}")
                    # Don't attempt individual inserts - let the caller handle the error
                    raise
            else:
                print(f"[{self.ticker}] ⚠️ No valid holdings data found")
        else:
            print(f"[{self.ticker}] ⚠️ No holdings data found")
    
    def _load_dividends(self):
        """Load dividend data for ETF."""
        print(f"[{self.ticker}] Loading dividend data...")
        
        # Check if dividends exist
        existing_count = self.session.query(Dividend).filter(Dividend.ticker_id == self.ticker_id).count()
        if existing_count > 0:
            print(f"[{self.ticker}] 🐬 {existing_count} dividend records already exist")
            return
        
        dividend_data = self.fmp_api.get_dividends(self.ticker)
        
        if dividend_data:
            dividend_records = []
            
            for dividend in dividend_data:
                dividend_record = {
                    'ticker_id': self.ticker_id,
                    'date': pd.to_datetime(dividend.get('date'), utc=True).date() if dividend.get('date') else None,
                    'recordDate': pd.to_datetime(dividend.get('recordDate'), utc=True).date() if dividend.get('recordDate') else None,
                    'paymentDate': pd.to_datetime(dividend.get('paymentDate'), utc=True).date() if dividend.get('paymentDate') else None,
                    'declarationDate': pd.to_datetime(dividend.get('declarationDate'), utc=True).date() if dividend.get('declarationDate') else None,
                    'adjDividend': dividend.get('adjDividend'),
                    'dividend': dividend.get('dividend'),
                    'yield_': dividend.get('yield'),
                    'frequency': dividend.get('frequency')
                }
                
                # Remove None values
                dividend_record = {k: v for k, v in dividend_record.items() if v is not None}
                
                if 'date' in dividend_record:  # Only add if we have a date
                    dividend_records.append(dividend_record)
            
            if dividend_records:
                self.session.bulk_insert_mappings(Dividend, dividend_records)
                self.session.flush()
                print(f"[{self.ticker}] ✅ Loaded {len(dividend_records)} dividend records")
            else:
                print(f"[{self.ticker}] ⚠️ No valid dividend data found")
        else:
            print(f"[{self.ticker}] ℹ️ No dividend data available")
    
    def load_etf_data(self, allow_partial_reload=False):
        """
        Main method to orchestrate loading all ETF data.
        
        Args:
            allow_partial_reload: If True, will complete missing data for existing tickers
        """
        print(f"\n{'='*60}")
        print(f"Loading ETF data: {self.ticker}")
        print(f"History range: {self.years_of_history} years")
        print(f"{'='*60}\n")
        
        self.session = MarketSession()
        
        try:
            # 1. Check if ticker already exists
            ticker_status = self._ensure_ticker_exists(allow_partial_reload)
            if ticker_status == False:
                print(f"\n[{self.ticker}] ⚠️ Aborting: Ticker already exists. Use allow_partial_reload=True to complete missing data.")
                return
            
            is_partial_reload = (ticker_status == "partial")
            
            # 2. Update quote data in ticker table (always update for latest info)
            if not is_partial_reload:
                self._update_ticker_quote_data()
            
            # 3. Load price data (skip if already exists during partial reload)
            if is_partial_reload:
                # Check if price data already exists
                price_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
                has_price_data = price_count > 0
                if has_price_data:
                    print(f"[{self.ticker}] ✓ Price data already exists ({price_count:,} records), skipping...")
            else:
                has_price_data = self._load_price_data_optimized()
                
                if not has_price_data:
                    print(f"\n[{self.ticker}] ⚠️ Aborting: No price data available for this ETF.")
                    print(f"[{self.ticker}] Rolling back all changes...")
                    self.session.rollback()
                    return
            
            # 4. Load daily prices
            self._load_daily_prices()

            # 5. Load ETF-specific data
            self._load_etf_info()
            self._load_etf_holdings()

            # 6. Load dividend data
            self._load_dividends()
            
            # Commit all changes
            self.session.commit()
            
            print(f"\n[{self.ticker}] 🎉 Successfully loaded all ETF data!")
            
        except Exception as e:
            print(f"\n[{self.ticker}] ❌ Error loading ETF data: {e}")
            self.session.rollback()
            raise
        finally:
            self.session.close()


def cleanup_etf_data(ticker):
    """
    Remove all data for an ETF from the database.
    Useful for cleaning up partial loads before re-running.
    
    Args:
        ticker: ETF ticker symbol to clean up
    """
    session = MarketSession()
    try:
        ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()
        if not ticker_obj:
            print(f"[{ticker}] No ticker found in database.")
            return
        
        ticker_id = ticker_obj.id
        
        # Delete in order of dependencies
        holdings_deleted = session.query(ETFHolding).filter(ETFHolding.ticker_id == ticker_id).delete()
        etf_info_deleted = session.query(ETFInfo).filter(ETFInfo.ticker_id == ticker_id).delete()
        dividends_deleted = session.query(Dividend).filter(Dividend.ticker_id == ticker_id).delete()
        prices_deleted = session.query(Price).filter(Price.ticker_id == ticker_id).delete()
        daily_prices_deleted = session.query(DailyPrices).filter(DailyPrices.ticker_id == ticker_id).delete()

        # Finally delete the ticker
        session.delete(ticker_obj)

        session.commit()

        print(f"[{ticker}] Cleanup complete:")
        print(f"  - Deleted {prices_deleted:,} intraday price records")
        print(f"  - Deleted {daily_prices_deleted:,} daily price records")
        print(f"  - Deleted {holdings_deleted} holdings")
        print(f"  - Deleted ETF info: {'Yes' if etf_info_deleted else 'No'}")
        print(f"  - Deleted {dividends_deleted} dividend records")
        print(f"  - Deleted ticker record")
        
    except Exception as e:
        print(f"[{ticker}] Error during cleanup: {e}")
        session.rollback()
    finally:
        session.close()


def load_single_etf(ticker, sector=None, industry=None, sub_industry=None, years_of_history=2, allow_partial_reload=False):
    """
    Convenience function to load a single ETF.
    
    Args:
        ticker: ETF ticker symbol
        sector: Optional sector classification
        industry: Optional industry classification
        sub_industry: Optional sub-industry classification
        years_of_history: Number of years of price history to fetch (default 2)
        allow_partial_reload: If True, completes missing data for existing tickers
    """
    loader = OptimizedETFDataLoader(
        ticker,
        sector=sector,
        industry=industry,
        sub_industry=sub_industry,
        years_of_history=years_of_history
    )
    loader.load_etf_data(allow_partial_reload=allow_partial_reload)


def load_multiple_etfs(etf_list, years_of_history=2):
    """
    Load multiple ETFs in sequence.
    
    Args:
        etf_list: List of tuples (ticker, sector, industry, sub_industry)
                  or list of ticker strings
        years_of_history: Number of years of price history to fetch
    """
    for item in etf_list:
        if isinstance(item, tuple):
            ticker, sector, industry, sub_industry = item
        else:
            ticker = item
            sector = industry = sub_industry = None
        
        print(f"\n{'#'*60}")
        print(f"# Processing ETF {etf_list.index(item) + 1}/{len(etf_list)}: {ticker}")
        print(f"{'#'*60}")
        
        try:
            load_single_etf(ticker, sector, industry, sub_industry, years_of_history)
            time.sleep(1)  # Small delay between ETFs
        except Exception as e:
            print(f"Failed to load {ticker}: {e}")
            continue


if __name__ == "__main__":
    # ============================================
    # HEALTHCARE / BIOTECH ETFs
    # ============================================

    load_single_etf(
        'XBI',
        sector="etf",
        industry="equity_etfs",
        sub_industry="sectors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IBB',
        sector="etf",
        industry="equity_etfs",
        sub_industry="sectors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'VHT',
        sector="etf",
        industry="equity_etfs",
        sub_industry="sectors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IYH',
        sector="etf",
        industry="equity_etfs",
        sub_industry="sectors",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # REIT ETFs
    # ============================================

    load_single_etf(
        'SCHH',
        sector="etf",
        industry="equity_etfs",
        sub_industry="u_s_sector_reits",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IYR',
        sector="etf",
        industry="equity_etfs",
        sub_industry="u_s_sector_reits",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'USRT',
        sector="etf",
        industry="equity_etfs",
        sub_industry="u_s_sector_reits",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'ICF',
        sector="etf",
        industry="equity_etfs",
        sub_industry="u_s_sector_reits",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # NUCLEAR / URANIUM ETFs
    # ============================================

    load_single_etf(
        'NUKZ',
        sector="etf",
        industry="equity_etfs",
        sub_industry="energy",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # BUFFER / DEFINED OUTCOME ETFs
    # ============================================

    load_single_etf(
        'BUFR',
        sector="etf",
        industry="alternative_etfs",
        sub_industry="strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'PJAN',
        sector="etf",
        industry="alternative_etfs",
        sub_industry="strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'UJAN',
        sector="etf",
        industry="alternative_etfs",
        sub_industry="strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'PSFF',
        sector="etf",
        industry="alternative_etfs",
        sub_industry="strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # ACTIVE SMALL CAP VALUE ETFs (Avantis/Dimensional)
    # ============================================

    load_single_etf(
        'AVUV',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'AVUS',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'DFAT',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'DFSV',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'DFAC',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'DFAI',
        sector="etf",
        industry="equity_etfs",
        sub_industry="developed_countries",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'AVDV',
        sector="etf",
        industry="equity_etfs",
        sub_industry="developed_countries",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'AVES',
        sector="etf",
        industry="equity_etfs",
        sub_industry="emerging_markets",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # ARK ETFs (Active Thematic)
    # ============================================

    load_single_etf(
        'ARKW',
        sector="etf",
        industry="equity_etfs",
        sub_industry="artificial_intelligence",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'ARKG',
        sector="etf",
        industry="equity_etfs",
        sub_industry="sectors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'ARKF',
        sector="etf",
        industry="equity_etfs",
        sub_industry="sectors",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # SMALL CAP ETFs (Core Index)
    # ============================================

    load_single_etf(
        'IWN',
        sector="etf",
        industry="equity_etfs",
        sub_industry="us_major_index",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IJS',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'SCHA',
        sector="etf",
        industry="equity_etfs",
        sub_industry="us_major_index",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'VIOO',
        sector="etf",
        industry="equity_etfs",
        sub_industry="us_major_index",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'CALF',
        sector="etf",
        industry="equity_etfs",
        sub_industry="fundamental",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # INTERNATIONAL SMALL CAP ETFs
    # ============================================

    load_single_etf(
        'VSS',
        sector="etf",
        industry="equity_etfs",
        sub_industry="single_country_small_and_mid_caps",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'DGS',
        sector="etf",
        industry="equity_etfs",
        sub_industry="single_country_small_and_mid_caps",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # ADDITIONAL DIVIDEND / INCOME ETFs
    # ============================================

    load_single_etf(
        'DIV',
        sector="etf",
        industry="equity_etfs",
        sub_industry="dividend_strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'SPYD',
        sector="etf",
        industry="equity_etfs",
        sub_industry="dividend_strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'HDV',
        sector="etf",
        industry="equity_etfs",
        sub_industry="dividend_strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'VIG',
        sector="etf",
        industry="equity_etfs",
        sub_industry="dividend_strategies",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # ESG / SUSTAINABLE ETFs
    # ============================================

    load_single_etf(
        'ESGU',
        sector="etf",
        industry="equity_etfs",
        sub_industry="environmental_social_and_corporate_governance",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'SUSA',
        sector="etf",
        industry="equity_etfs",
        sub_industry="environmental_social_and_corporate_governance",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # MID CAP ETFs
    # ============================================

    load_single_etf(
        'VO',
        sector="etf",
        industry="equity_etfs",
        sub_industry="us_major_index",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IJK',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IJJ',
        sector="etf",
        industry="equity_etfs",
        sub_industry="factors",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # ADDITIONAL TREASURY / BOND ETFs
    # ============================================

    load_single_etf(
        'IEI',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="treasuries",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'SHV',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="treasuries",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'GOVT',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="treasuries",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'STIP',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="interest_rate_and_inflation_hedge",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'TFLR',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="senior_loans",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # MUNICIPAL BOND ETFs
    # ============================================

    load_single_etf(
        'MUB',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="u_s_municipal_bond_etfs",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'VTEB',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="u_s_municipal_bond_etfs",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # INTERNATIONAL BOND ETFs
    # ============================================

    load_single_etf(
        'IAGG',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="sovereign",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'IGOV',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="sovereign",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'EMB',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="emerging_markets",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'VWOB',
        sector="etf",
        industry="fixed_income_etfs",
        sub_industry="emerging_markets",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # GLOBAL / INTERNATIONAL EQUITY ETFs
    # ============================================

    load_single_etf(
        'ACWX',
        sector="etf",
        industry="equity_etfs",
        sub_industry="global_equities",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'CWI',
        sector="etf",
        industry="equity_etfs",
        sub_industry="global_equities",
        years_of_history=5,
        allow_partial_reload=False
    )

    # ============================================
    # ADDITIONAL FACTOR / SMART BETA ETFs
    # ============================================

    load_single_etf(
        'FNDX',
        sector="etf",
        industry="equity_etfs",
        sub_industry="fundamental",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'RSP',
        sector="etf",
        industry="equity_etfs",
        sub_industry="equal_weighted",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'QQQE',
        sector="etf",
        industry="equity_etfs",
        sub_industry="equal_weighted",
        years_of_history=5,
        allow_partial_reload=False
    )

    load_single_etf(
        'QQQM',
        sector="etf",
        industry="equity_etfs",
        sub_industry="us_major_index",
        years_of_history=5,
        allow_partial_reload=False
    )
