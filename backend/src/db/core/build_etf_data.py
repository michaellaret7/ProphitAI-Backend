from backend.src.repositories.price_data import get_price_data_15_mins
from backend.src.db.core.db_config import MarketSession, market_engine
from backend.src.db.core.market_data_models import (
    Ticker, Price, ETFInfo, ETFHolding, Dividend
)
from backend.src.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta
from sqlalchemy import insert, update
import pandas as pd
import time
import io
import csv
import uuid


def bulk_insert_with_copy(session, table_name, data_to_insert, ordered_columns):
    """
    Performs a bulk insert using PostgreSQL's COPY command for high performance.
    Raises exception on failure.
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
        copy_sql = f"COPY {table_name} ({','.join(ordered_columns)}) FROM STDIN WITH (FORMAT CSV)"
        cursor.copy_expert(sql=copy_sql, file=string_buffer)
        raw_connection.commit()
        print("✅ Bulk insertion successful.")
    except Exception as e:
        print(f"❌ Error during COPY: {e}")
        raw_connection.rollback()
        raise  # Re-raise the exception to be handled by the caller
    finally:
        cursor.close()


class ETFDataLoader:
    """
    Loads comprehensive ETF data into the database for a single ticker.
    
    Args:
        ticker (str): The ETF ticker symbol (e.g., 'SPY', 'QQQ')
        sector (str, optional): The sector classification for the ETF (e.g., 'ETF')
        industry (str, optional): The industry classification (e.g., 'Equity ETF', 'Bond ETF')
        sub_industry (str, optional): More specific classification (e.g., 'Large Cap', 'Technology')
    """
    def __init__(self, ticker, sector=None, industry=None, sub_industry=None):
        self.ticker = ticker.upper()
        self.sector = sector
        self.industry = industry
        self.sub_industry = sub_industry
        self.fmp_api = FMP_API_DATA()
        self.ticker_id = None
        self.session = None
        
    def _ensure_ticker_exists(self):
        """Check if ticker exists in database. Returns True if ticker is new, False if it already exists."""
        ticker_obj = self.session.query(Ticker).filter(Ticker.ticker == self.ticker).first()
        
        if ticker_obj:
            # Ticker already exists - set ticker_id and abort
            self.ticker_id = ticker_obj.id
            print(f"[{self.ticker}] ⚠️ Ticker already exists in database.")
            if ticker_obj.is_etf:
                print(f"[{self.ticker}] ℹ️ Already marked as ETF.")
            else:
                print(f"[{self.ticker}] ℹ️ Exists as a stock (not ETF).")
            
            # Check if it already has price data
            price_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
            if price_count > 0:
                print(f"[{self.ticker}] ℹ️ Has {price_count:,} price records.")
            
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
                'last_updated': datetime.now()
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            if update_data:
                self.session.query(Ticker).filter(Ticker.id == self.ticker_id).update(update_data)
                self.session.flush()
                print(f"[{self.ticker}] ✅ Updated quote data")
    
    def _load_price_data(self):
        """Load historical price data for the ETF. Returns True if data was loaded successfully."""
        print(f"[{self.ticker}] Loading price data...")
        
        # Check if price data already exists
        existing_count = self.session.query(Price).filter(Price.ticker_id == self.ticker_id).count()
        if existing_count > 0:
            print(f"[{self.ticker}] 🐬 {existing_count:,} price records already exist")
            return True  # Price data exists, so we can continue
        
        # Fetch price data using repository
        start_date = datetime.now() - timedelta(days=365*4)  # 6 years of data
        end_date = datetime.now()
        
        try:
            price_data = get_price_data_15_mins(self.ticker, start_date, end_date)
            
            if price_data.empty:
                # Try FMP intraday endpoint
                print(f"[{self.ticker}] Trying FMP intraday endpoint...")
                price_data = self._get_intraday_prices()
            
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
                print(f"[{self.ticker}] ❌ No price data found - ETF will not be added to database")
                return False
                
        except Exception as e:
            print(f"[{self.ticker}] ✗ Error loading price data: {e}")
            return False
    
    def _get_intraday_prices(self):
        """Fetch intraday prices from FMP API."""
        all_data = []
        to_date = datetime.now()
        limit_date = datetime.now() - timedelta(days=6*365)
        call_count = 0
        
        print(f"[{self.ticker}] Starting intraday price fetch from {limit_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
        
        while to_date > limit_date:
            call_count += 1
            from_date = to_date - timedelta(weeks=2)
            if from_date < limit_date:
                from_date = limit_date
            
            print(f"[{self.ticker}] API call #{call_count}: Fetching {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
            
            price_chunk = self.fmp_api.get_intraday_prices_for_ticker(
                ticker=self.ticker,
                from_date=from_date,
                to_date=to_date
            )
            
            if not price_chunk:
                print(f"[{self.ticker}] No data returned for this period, stopping...")
                break
            
            all_data.extend(price_chunk)
            print(f"[{self.ticker}] Received {len(price_chunk)} records. Total so far: {len(all_data)}")
            
            # Get oldest date to continue backwards
            oldest_date_str = price_chunk[-1]['date']
            to_date = datetime.strptime(oldest_date_str, '%Y-%m-%d %H:%M:%S')
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df.drop_duplicates(subset=['date'], inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values(by='date', inplace=True)
        
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
                'inceptionDate': pd.to_datetime(info.get('inceptionDate')) if info.get('inceptionDate') else None,
                'nav': info.get('nav'),
                'navCurrency': info.get('navCurrency'),
                'holdingsCount': info.get('holdingsCount'),
                'updatedAt': datetime.now(),
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
        
        # Delete existing holdings to refresh
        self.session.query(ETFHolding).filter(ETFHolding.ticker_id == self.ticker_id).delete()
        
        holdings_data = self.fmp_api.get_etf_holdings(self.ticker)
        
        if holdings_data:
            holdings_records = []
            
            for holding in holdings_data:
                holding_record = {
                    'ticker_id': self.ticker_id,
                    'asset': holding.get('asset', ''),
                    'name': holding.get('name'),
                    'isin': holding.get('isin'),
                    'securitycusip': holding.get('cusip'),  # lowercase for PostgreSQL
                    'sharesnumber': holding.get('sharesNumber'),  # lowercase for PostgreSQL
                    'weightpercentage': holding.get('weightPercentage'),  # lowercase for PostgreSQL
                    'marketvalue': holding.get('marketValue'),  # lowercase for PostgreSQL
                    'updatedat': datetime.now()  # lowercase for PostgreSQL
                }
                
                # Skip if no asset identifier
                if holding_record['asset']:
                    holdings_records.append(holding_record)
            
            if holdings_records:
                # Bulk insert holdings
                # Note: PostgreSQL lowercases unquoted column names, so we use lowercase here
                ordered_columns = ['ticker_id', 'asset', 'name', 'isin', 'securitycusip', 
                                 'sharesnumber', 'weightpercentage', 'marketvalue', 'updatedat']
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
                    'date': pd.to_datetime(dividend.get('date')).date() if dividend.get('date') else None,
                    'recordDate': pd.to_datetime(dividend.get('recordDate')).date() if dividend.get('recordDate') else None,
                    'paymentDate': pd.to_datetime(dividend.get('paymentDate')).date() if dividend.get('paymentDate') else None,
                    'declarationDate': pd.to_datetime(dividend.get('declarationDate')).date() if dividend.get('declarationDate') else None,
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
    
    def load_etf_data(self):
        """Main method to orchestrate loading all ETF data."""
        print(f"\n{'='*60}")
        print(f"Loading all data for ETF: {self.ticker}")
        print(f"{'='*60}\n")
        
        self.session = MarketSession()
        
        try:
            # 1. Check if ticker already exists - quit if it does
            is_new_ticker = self._ensure_ticker_exists()
            if not is_new_ticker:
                print(f"\n[{self.ticker}] ⚠️ Aborting: Ticker already exists in database.")
                print(f"[{self.ticker}] No changes made.")
                return
            
            # 2. Update quote data in ticker table
            self._update_ticker_quote_data()
            
            # 3. Load price data - CRITICAL: If no price data, abort entire process
            has_price_data = self._load_price_data()
            
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


if __name__ == "__main__":
    # Example usage
    etf_ticker = "UTEN"
    ticker2 = "VIXY"

    # session = MarketSession()
    # unique_industries = session.query(Ticker.sub_industry).filter(Ticker.sector == "etf", Ticker.industry == 'fixed_income_etfs').distinct().all()
    # for industry in unique_industries:
    #     print(industry[0])  # industry[0] because query returns tuples
    
    # Option 2: Specify classification
    loader = ETFDataLoader(
        etf_ticker,
        sector="etf",
        industry="alternative_etfs",
        sub_industry="volatility"
    )
    
    loader.load_etf_data()