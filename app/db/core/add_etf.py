from app.repositories.price_data import get_price_data_15_mins
from app.db.core.db_config import MarketSession, market_engine
from app.db.core.models.market_data_models import (
    Ticker, Price, ETFInfo, ETFHolding, Dividend
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta, timezone
from sqlalchemy import insert, update
import pandas as pd
import time
import io
import csv
import uuid


def bulk_insert_with_copy(session, table_name, data_to_insert, ordered_columns):
    """
    Performs a bulk insert using PostgreSQL's COPY command for high performance.
    IMPORTANT: Does NOT commit - lets the calling code manage the transaction.
    NOTE: All timestamps are in UTC timezone for consistency.
    """
    if not data_to_insert:
        print("No new data to insert.")
        return
    
    print(f"Preparing to insert {len(data_to_insert):,} records using COPY.")
    
    string_buffer = io.StringIO()
    writer = csv.writer(string_buffer)
    
    for row_dict in data_to_insert:
        writer.writerow([row_dict.get(col) for col in ordered_columns])
        
    string_buffer.seek(0)
    
    raw_connection = session.connection().connection
    cursor = raw_connection.cursor()
    
    try:
        # Quote column names to preserve case sensitivity in PostgreSQL
        quoted_columns = ','.join([f'"{col}"' for col in ordered_columns])
        copy_sql = f"COPY {table_name} ({quoted_columns}) FROM STDIN WITH (FORMAT CSV)"
        cursor.copy_expert(sql=copy_sql, file=string_buffer)
        # DO NOT COMMIT HERE - let the session handle the transaction
        print("✅ Bulk insertion prepared (will commit with session).")
    except Exception as e:
        print(f"❌ Error during COPY: {e}")
        raise  # Let the session handle rollback
    finally:
        cursor.close()


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
        
        # Check for existing holdings first
        existing_holdings = self.session.query(ETFHolding).filter(ETFHolding.ticker_id == self.ticker_id).all()
        if existing_holdings:
            print(f"[{self.ticker}] Found {len(existing_holdings)} existing holdings to remove")
            for h in existing_holdings[:3]:  # Show first 3 for debugging
                print(f"  - Asset: '{h.asset}' Name: {h.name}")
        
        # Delete existing holdings to refresh
        deleted_count = self.session.query(ETFHolding).filter(ETFHolding.ticker_id == self.ticker_id).delete()
        if deleted_count > 0:
            print(f"[{self.ticker}] Removed {deleted_count} existing holdings")
            self.session.flush()  # Make deletion visible within the transaction
        
        holdings_data = self.fmp_api.get_etf_holdings(self.ticker)
        
        if holdings_data:
            holdings_records = []
            
            for holding in holdings_data:
                # Get asset and clean it (remove extra whitespace)
                asset = (holding.get('asset', '') or '').strip()
                
                # Skip if no asset identifier or empty after stripping
                if not asset:
                    continue
                
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
            
            if holdings_records:
                # Bulk insert holdings - using camelCase to match database columns
                ordered_columns = ['ticker_id', 'asset', 'name', 'isin', 'securityCusip', 
                                 'sharesNumber', 'weightPercentage', 'marketValue', 'updatedAt']
                bulk_insert_with_copy(self.session, ETFHolding.__table__.fullname, holdings_records, ordered_columns)
                
                print(f"[{self.ticker}] ✅ Loaded {len(holdings_records)} holdings")
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
            
            # 4. Load ETF-specific data
            self._load_etf_info()
            self._load_etf_holdings()
            
            # 5. Load dividend data
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
        
        # Finally delete the ticker
        session.delete(ticker_obj)
        
        session.commit()
        
        print(f"[{ticker}] Cleanup complete:")
        print(f"  - Deleted {prices_deleted:,} price records")
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
    load_single_etf(
        "RSPS", 
        sector="etf", 
        industry="equity_etfs", 
        sub_industry="equal_weighted", 
        years_of_history=4,  # Use 4 years for faster loading
        allow_partial_reload=False  # This will complete missing data
    )

