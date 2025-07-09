import json
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.testing.db_test.db_config import MarketSession, market_engine
from backend.testing.db_test.market_data_models import Ticker
from backend.src.utils.determine_etf import is_etf_ticker
from backend.src.utils.file_utils import get_schema_path

def clear_ticker_universe():
    """
    Clears all existing tickers from the ticker_universe.tickers table.
    USE WITH CAUTION!
    """
    session = MarketSession()
    try:
        count = session.query(Ticker).count()
        if count > 0:
            response = input(f"Are you sure you want to delete {count} existing tickers? (yes/no): ")
            if response.lower() == 'yes':
                session.query(Ticker).delete()
                session.commit()
                print(f"Deleted {count} tickers from the database.")
            else:
                print("Operation cancelled.")
    except Exception as e:
        print(f"Error clearing tickers: {e}")
        session.rollback()
    finally:
        session.close()

def build_ticker_universe():
    """
    Reads database_schemas.json and populates the ticker_universe.tickers table
    with all tickers, including their sector, industry, sub_industry, and is_etf flag.
    """
    # Get path to database schema
    schema_path = str(get_schema_path())
    
    # Read the database schema
    with open(schema_path, 'r') as f:
        data = json.load(f)
    
    # Create database session
    session = MarketSession()
    
    try:
        # Counter for tracking progress
        total_tickers = 0
        processed_tickers = 0
        duplicate_tickers = 0
        error_tickers = 0
        
        # Collect all tickers first to show total count
        all_tickers = []
        
        # First pass: collect all tickers
        for sector_key, sector_data in data.items():
            if 'schemas' not in sector_data:
                continue
                
            for industry_key, industry_data in sector_data['schemas'].items():
                tables = industry_data.get('tables', {})
                for sub_industry_key, table_data in tables.items():
                    tickers = table_data.get('tickers', [])
                    for ticker_symbol in tickers:
                        all_tickers.append({
                            'ticker': ticker_symbol,
                            'sector': sector_key,
                            'industry': industry_key,
                            'sub_industry': sub_industry_key
                        })
        
        total_tickers = len(all_tickers)
        print(f"Found {total_tickers} tickers to process...")
        
        # Second pass: process each ticker
        for ticker_data in all_tickers:
            ticker_symbol = ticker_data['ticker']
            
            try:
                # Check if ticker already exists
                existing_ticker = session.query(Ticker).filter_by(ticker=ticker_symbol).first()
                if existing_ticker:
                    duplicate_tickers += 1
                    continue
                
                # Determine if it's an ETF
                is_etf = is_etf_ticker(ticker_symbol)
                
                # Create new ticker entry
                ticker = Ticker(
                    id=uuid.uuid4(),
                    ticker=ticker_symbol,
                    sector=ticker_data['sector'],
                    industry=ticker_data['industry'],
                    sub_industry=ticker_data['sub_industry'],
                    is_etf=is_etf
                )
                
                session.add(ticker)
                processed_tickers += 1
                
                # Commit in batches for better performance
                if processed_tickers % 100 == 0:
                    session.commit()
                    print(f"Processed {processed_tickers}/{total_tickers} tickers...")
                    
            except IntegrityError as e:
                # Handle unique constraint violations
                session.rollback()
                duplicate_tickers += 1
                continue
            except Exception as e:
                # Log other errors but continue processing
                print(f"Error processing {ticker_symbol}: {e}")
                session.rollback()
                error_tickers += 1
                continue
        
        # Final commit for any remaining tickers
        session.commit()
        
        print("\n" + "="*50)
        print("SUMMARY:")
        print(f"Total tickers found: {total_tickers}")
        print(f"Successfully processed: {processed_tickers}")
        print(f"Duplicates skipped: {duplicate_tickers}")
        print(f"Errors encountered: {error_tickers}")
        print("="*50)
        
    except Exception as e:
        print(f"Fatal error occurred: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def verify_ticker_universe():
    """
    Verifies the ticker universe was populated correctly by showing counts
    by sector and checking ETF counts.
    """
    session = MarketSession()
    
    try:
        # Total ticker count
        total_count = session.query(Ticker).count()
        print(f"\nTotal tickers in universe: {total_count}")
        
        # ETF count
        etf_count = session.query(Ticker).filter_by(is_etf=True).count()
        print(f"Total ETFs: {etf_count}")
        print(f"Total non-ETF equities: {total_count - etf_count}")
        
        # Count by sector
        print("\nTickers by sector:")
        print("-" * 60)
        
        from sqlalchemy import func
        sector_counts = session.query(
            Ticker.sector, 
            func.count(Ticker.id).label('count')
        ).group_by(Ticker.sector).order_by('count').all()
        
        for sector, count in sector_counts:
            print(f"{sector:<45} {count:>5}")
        
        # Show sample tickers
        print("\nSample tickers:")
        print("-" * 80)
        sample_tickers = session.query(Ticker).limit(10).all()
        for ticker in sample_tickers:
            print(f"{ticker.ticker:<6} | Sector: {ticker.sector[:30]:<30} | ETF: {ticker.is_etf}")
            
    finally:
        session.close()

def get_tickers_by_sub_industry(sub_industry_name):
    """
    Get all tickers from a specific sub-industry.
    
    Args:
        sub_industry_name (str): The name of the sub-industry to query
        
    Returns:
        list: List of Ticker objects matching the sub-industry
    """
    session = MarketSession()
    
    try:
        # Query all tickers with the specified sub_industry
        tickers = session.query(Ticker).filter(
            Ticker.sub_industry == sub_industry_name
        ).all()
        
        return tickers
        
    finally:
        session.close()

def get_tickers_by_industry(industry_name):
    """
    Get all tickers from a specific industry.
    
    Args:
        industry_name (str): The name of the industry to query
        
    Returns:
        list: List of Ticker objects matching the industry
    """
    session = MarketSession()
    
    try:
        # Query all tickers with the specified industry
        tickers = session.query(Ticker).filter(
            Ticker.industry == industry_name
        ).all()
        
        return tickers
        
    finally:
        session.close()

def get_tickers_by_sector(sector_name):
    """
    Get all tickers from a specific sector.
    
    Args:
        sector_name (str): The name of the sector to query
        
    Returns:
        list: List of Ticker objects matching the sector
    """
    session = MarketSession()
    
    try:
        # Query all tickers with the specified sector
        tickers = session.query(Ticker).filter(
            Ticker.sector == sector_name
        ).all()
        
        return tickers
        
    finally:
        session.close()

def migrate_ticker_table():
    """
    Adds the new quote data columns to the existing ticker table.
    Uses raw SQL ALTER TABLE commands.
    """
    from sqlalchemy import text
    from backend.testing.db_test.db_config import market_engine
    
    print("Migrating ticker table to add quote data columns...")
    
    try:
        with market_engine.connect() as conn:
            # Add each column one by one
            columns_to_add = [
                ("price", "FLOAT"),
                ("market_cap", "NUMERIC"),
                ("avg_volume", "NUMERIC"),
                ("eps", "FLOAT"),
                ("pe", "FLOAT"),
                ("dollar_volume", "NUMERIC"),
                ("last_updated", "TIMESTAMP")
            ]
            
            for column_name, column_type in columns_to_add:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE ticker_universe.tickers 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
                    """))
                    print(f"✓ Added column: {column_name}")
                except Exception as e:
                    print(f"✗ Error adding column {column_name}: {e}")
            
            conn.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        raise

def update_ticker_quote_data(ticker_symbol=None, batch_size=10):
    """
    Updates quote data (price, marketCap, avgVolume, eps, pe, dollarVolume) for tickers.
    
    Args:
        ticker_symbol: Specific ticker to update. If None, updates all tickers.
        batch_size: Number of tickers to process before committing
    """
    from backend.testing.db_test.test_price_data import FMP_API_DATA
    from datetime import datetime
    from decimal import Decimal
    
    session = MarketSession()
    fmp_api = FMP_API_DATA()
    
    try:
        # Get tickers to update
        if ticker_symbol:
            tickers = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).all()
        else:
            tickers = session.query(Ticker).all()
        
        total_tickers = len(tickers)
        print(f"\nUpdating quote data for {total_tickers} tickers...")
        
        updated_count = 0
        error_count = 0
        
        for i, ticker in enumerate(tickers):
            try:
                # Fetch quote data from FMP
                quote_data = fmp_api.get_full_quote(ticker.ticker)
                
                if quote_data and len(quote_data) > 0:
                    quote = quote_data[0]
                    
                    # Update ticker with quote data
                    ticker.price = quote.get('price')
                    ticker.market_cap = Decimal(str(quote.get('marketCap', 0))) if quote.get('marketCap') else None
                    ticker.avg_volume = Decimal(str(quote.get('avgVolume', 0))) if quote.get('avgVolume') else None
                    ticker.eps = quote.get('eps')
                    ticker.pe = quote.get('pe')
                    
                    # Calculate dollar volume
                    if ticker.price and ticker.avg_volume:
                        ticker.dollar_volume = Decimal(str(ticker.price)) * ticker.avg_volume
                    else:
                        ticker.dollar_volume = None
                    
                    ticker.last_updated = datetime.now()
                    
                    updated_count += 1
                    
                    if updated_count % batch_size == 0:
                        session.commit()
                        print(f"Progress: {i+1}/{total_tickers} - Updated {updated_count} tickers...")
                
            except Exception as e:
                print(f"Error updating {ticker.ticker}: {e}")
                error_count += 1
                continue
        
        # Final commit
        session.commit()
        
        print("\n" + "="*50)
        print("UPDATE SUMMARY:")
        print(f"Total tickers: {total_tickers}")
        print(f"Successfully updated: {updated_count}")
        print(f"Errors: {error_count}")
        print("="*50)
        
    except Exception as e:
        session.rollback()
        print(f"Fatal error occurred: {e}")
        raise
    finally:
        session.close()

def update_all_quote_data_parallel(max_workers=10):
    """
    Updates quote data for all tickers using parallel processing.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from backend.testing.db_test.test_price_data import FMP_API_DATA
    from datetime import datetime
    from decimal import Decimal
    import time
    
    def update_single_ticker(ticker_symbol):
        """Thread-safe function to update a single ticker"""
        session = MarketSession()
        fmp_api = FMP_API_DATA()
        
        try:
            ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()
            if not ticker:
                return ticker_symbol, False, "Not found"
            
            # Fetch quote data
            quote_data = fmp_api.get_full_quote(ticker_symbol)
            
            if quote_data and len(quote_data) > 0:
                quote = quote_data[0]
                
                # Update ticker
                ticker.price = quote.get('price')
                ticker.market_cap = Decimal(str(quote.get('marketCap', 0))) if quote.get('marketCap') else None
                ticker.avg_volume = Decimal(str(quote.get('avgVolume', 0))) if quote.get('avgVolume') else None
                ticker.eps = quote.get('eps')
                ticker.pe = quote.get('pe')
                
                # Calculate dollar volume
                if ticker.price and ticker.avg_volume:
                    ticker.dollar_volume = Decimal(str(ticker.price)) * ticker.avg_volume
                
                ticker.last_updated = datetime.now()
                
                session.commit()
                return ticker_symbol, True, "Success"
            else:
                return ticker_symbol, False, "No quote data"
                
        except Exception as e:
            session.rollback()
            return ticker_symbol, False, f"Error: {str(e)}"
        finally:
            session.close()
    
    # Get all ticker symbols
    session = MarketSession()
    ticker_symbols = [t.ticker for t in session.query(Ticker).all()]
    session.close()
    
    print(f"\nUpdating quote data for {len(ticker_symbols)} tickers with {max_workers} workers...")
    start_time = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(update_single_ticker, ticker): ticker 
                           for ticker in ticker_symbols}
        
        for future in as_completed(future_to_ticker):
            result = future.result()
            results.append(result)
            
            # Print progress every 100 tickers
            if len(results) % 100 == 0:
                print(f"Progress: {len(results)}/{len(ticker_symbols)}")
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = sum(1 for _, success, _ in results if success)
    
    print("\n" + "="*60)
    print("QUOTE UPDATE SUMMARY:")
    print(f"Total tickers: {len(results)}")
    print(f"Successful updates: {success_count}")
    print(f"Failed updates: {len(results) - success_count}")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Average time per ticker: {duration/len(results):.3f} seconds")
    print("="*60)

def main():
    """Main function with menu options"""
    print("Ticker Universe Builder")
    print("=" * 50)
    print("1. Build ticker universe (add new tickers)")
    print("2. Clear and rebuild ticker universe")
    print("3. Verify ticker universe")
    print("4. Migrate table (add quote columns)")
    print("5. Update quote data for all tickers")
    print("6. Update quote data for specific ticker")
    print("7. Exit")
    
    choice = input("\nEnter your choice (1-7): ")
    
    if choice == '1':
        print("\nBuilding ticker universe from database schema...")
        build_ticker_universe()
        verify_ticker_universe()
    elif choice == '2':
        print("\nClearing existing tickers...")
        clear_ticker_universe()
        print("\nBuilding ticker universe from database schema...")
        build_ticker_universe()
        verify_ticker_universe()
    elif choice == '3':
        verify_ticker_universe()
    elif choice == '4':
        print("\nMigrating ticker table to add quote columns...")
        migrate_ticker_table()
    elif choice == '5':
        print("\nUpdating quote data for all tickers...")
        # Ask if user wants parallel processing
        parallel = input("Use parallel processing? (yes/no): ")
        if parallel.lower() == 'yes':
            workers = input("Number of workers (default 10): ") or "10"
            update_all_quote_data_parallel(int(workers))
        else:
            update_ticker_quote_data()
    elif choice == '6':
        ticker = input("Enter ticker symbol: ").upper()
        print(f"\nUpdating quote data for {ticker}...")
        update_ticker_quote_data(ticker)
    elif choice == '7':
        print("Exiting...")
    else:
        print("Invalid choice!")


