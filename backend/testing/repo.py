import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID
from backend.src.utils.database import get_connection
from backend.testing.repo_models import UserPortfolioHoldings, UserInfo, UserCreatedPortfolio, UserPortfolioAllocations, UserPortfolioThesis, UserAvailablePortfolios, UserInvestmentInformation, PriceData

load_dotenv()

class UserCurrentPortfolioRepository:
    """Minimalistic and efficient repository for portfolio data queries."""
    def __init__(self):
        pass
    
    def fetch_holdings(self, email: str) -> List[UserPortfolioHoldings]:
        """
        Fetch user portfolio holdings by email.
        Args:
            email: User email address
        Returns:
            List of UserPortfolioHolding objects with validated data
        """
        conn = get_connection("user_data")
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM public.user_portfolios
                    WHERE email = %s
                """, (email,))
                
                rows = cursor.fetchall()
                
                # Convert to Pydantic objects with validation
                holdings = []
                for row in rows:
                    try:
                        holding = UserPortfolioHoldings(**dict(row))
                        holdings.append(holding)
                    except Exception as e:
                        print(f"Error validating holding data: {e}")
                        print(f"Raw data: {dict(row)}")
                        # Skip invalid records
                        continue
                
                return holdings
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return []
        finally:
            conn.close()

class UserInfoRepository:
    def __init__(self):
        pass
    
    def fetch_user_by_email(self, email: str) -> Optional[UserInfo]:
        """
        Fetch user information by email address.
        Args:
            email: User email address
        Returns:
            UserInfo object if found, None otherwise
        """
        conn = get_connection("user_data")
        if not conn:
            return None

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM public.users
                    WHERE email = %s
                """, (email,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                try:
                    return UserInfo(**dict(row))
                except Exception as e:
                    print(f"Error validating user data: {e}")
                    print(f"Raw data: {dict(row)}")
                    return None
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()
    
    def fetch_user_by_id(self, user_id: str) -> Optional[UserInfo]:
        """
        Fetch user information by user ID.
        Args:
            user_id: User ID string
        Returns:
            UserInfo object if found, None otherwise
        """
        conn = get_connection("user_data")
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM public.users
                    WHERE id = %s
                """, (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                try:
                    return UserInfo(**dict(row))
                except Exception as e:
                    print(f"Error validating user data: {e}")
                    print(f"Raw data: {dict(row)}")
                    return None
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()

class UserCreatedPortfolioRepository:
    def __init__(self):
        pass
    
    def fetch_portfolio(self, portfolio_id: UUID, user_id: Optional[str] = None, email: Optional[str] = None) -> List[UserCreatedPortfolio]:
        if not user_id and not email:
            raise ValueError("Either user_id or email must be provided")  
        
        conn = get_connection("portfolio_results")
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Single query that handles None values correctly
                cursor.execute("""
                    SELECT * FROM public.final_portfolio 
                    WHERE portfolio_id = %s 
                    AND (user_id = %s OR email = %s)
                """, (portfolio_id, user_id, email))
                
                rows = cursor.fetchall()
                return [UserCreatedPortfolio(**dict(row)) for row in rows]
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return []
        finally:
            conn.close()
    
    def fetch_portfolio_allocations(self, portfolio_id: UUID, user_id: Optional[str] = None, email: Optional[str] = None) -> List[UserPortfolioAllocations]:
        conn = get_connection("portfolio_results")
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM public.portfolio_sector_allocation
                    WHERE portfolio_id = %s
                    AND (user_id = %s OR email = %s)
                """, (portfolio_id, user_id, email))

                rows = cursor.fetchall()
                return [UserPortfolioAllocations(**dict(row)) for row in rows]
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return []
        finally:
            conn.close()
    
    def fetch_portfolio_thesis(self, portfolio_id: UUID, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[UserPortfolioThesis]:
        conn = get_connection("portfolio_results")
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT portfolio_id, portfolio_name, thesis, user_id, email
                    FROM public.portfolio_thesis
                    WHERE portfolio_id = %s
                    AND (user_id = %s OR email = %s)
                """, (portfolio_id, user_id, email))
                
                row = cursor.fetchone()
                if row:
                    return UserPortfolioThesis(**dict(row))
                return None
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()
    
    def fetch_available_portfolios(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[UserAvailablePortfolios]:
        conn = get_connection("portfolio_results")
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT portfolio_id, portfolio_name, created_at, user_id, email
                    FROM public.portfolios
                    WHERE user_id = %s OR email = %s
                """, (user_id, email))
                
                rows = cursor.fetchall()
                return [UserAvailablePortfolios(**dict(row)) for row in rows]
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return []
        finally:
            conn.close()
    
    def fetch_user_investment_information(self, portfolio_id: UUID) -> Optional[UserInvestmentInformation]:
        conn = get_connection("portfolio_results")
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM public.user_information
                    WHERE portfolio_id = %s
                """, (portfolio_id,))
                
                row = cursor.fetchone()
                if row:
                    return UserInvestmentInformation(**dict(row))
                return None
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()

class EquityPriceDataRepository:
    def __init__(self):
        pass
    
    def fetch_equity_price_data(self, ticker: str, start_date: datetime, end_date: datetime) -> List[PriceData]:
        # Try different database connections to find the ticker
        possible_databases = [
            "equity_sector_communication_services_prices",
            "equity_sector_consumer_discretionary_prices",
            "equity_sector_consumer_staples_prices",
            "equity_sector_energy_prices",
            "equity_sector_financials_prices",
            "equity_sector_health_care_prices",
            "equity_sector_industrials_prices",
            "equity_sector_information_technology_prices",
            "equity_sector_materials_prices",
            "equity_sector_real_estate_prices",
            "equity_sector_utilities_prices"
        ]
        
        for db_name in possible_databases:
            conn = get_connection(db_name)
            if not conn:
                continue
                
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # First, find which schema contains the ticker table
                    cursor.execute("""
                        SELECT schemaname, tablename 
                        FROM pg_tables 
                        WHERE tablename = %s
                    """, (ticker,))
                    
                    table_info = cursor.fetchone()
                    if table_info:
                        schema_name = table_info['schemaname']
                        
                        # Now query the actual data
                        cursor.execute(f"""
                            SELECT date, open, high, low, close, volume
                            FROM {schema_name}.{ticker}
                            WHERE date >= %s AND date <= %s
                            ORDER BY date
                        """, (start_date, end_date))
                        
                        rows = cursor.fetchall()
                        conn.close()
                        return [PriceData(**dict(row)) for row in rows]
                
            except psycopg2.Error as e:
                print(f"Error searching in {db_name}: {e}")
                continue
            finally:
                conn.close()
        
        print(f"Ticker '{ticker}' not found in any database")
        return []

class ETFDataRepository:
    def __init__(self):
        pass
    
    def fetch_etf_data(self, ticker: str, start_date: datetime, end_date: datetime) -> List[PriceData]:
        # Convert ticker to lowercase for table lookup
        ticker_lower = ticker.lower()
        
        # ETF price schemas to search through
        etf_schemas = [
            "equity_etfs_prices",
            "cryptocurrency_etfs_prices", 
            "fixed_income_etfs_prices",
            "commodity_etfs_prices",
            "alternative_etfs_prices"
        ]
        
        conn = get_connection("etf_prices")
        if not conn:
            print("Could not connect to etf_prices database")
            return []
            
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Search through each ETF schema for the ticker table
                for schema_name in etf_schemas:
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = %s AND tablename = %s
                    """, (schema_name, ticker_lower))
                    
                    table_info = cursor.fetchone()
                    if table_info:
                        # Found the ticker table, now query the data
                        cursor.execute(f"""
                            SELECT datetime as date, open, high, low, close, volume
                            FROM {schema_name}.{ticker_lower}
                            WHERE datetime >= %s AND datetime <= %s
                            ORDER BY datetime
                        """, (start_date, end_date))
                        
                        rows = cursor.fetchall()
                        return [PriceData(**dict(row)) for row in rows]
                
                print(f"Ticker '{ticker}' not found in any ETF price schema")
                return []
            
        except psycopg2.Error as e:
            print(f"Error searching in etf_prices database: {e}")
            return []
        finally:
            conn.close()

if __name__ == "__main__":
    equity_price_data_repo = EquityPriceDataRepository()
    portfolio_repo = UserCreatedPortfolioRepository()

    # portfolio = portfolio_repo.fetch_portfolio(portfolio_id="0f5bcbe1-6148-4673-80e9-263e08e35fbf", user_id="user_01JXG39MMAVW1P3XVGX7YHN2DT")
    # print(portfolio)
    
    # equity_price_data = equity_price_data_repo.fetch_equity_price_data(ticker="msft", start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 10))
    # print(equity_price_data)

    etf_data_repo = ETFDataRepository()
    etf_data = etf_data_repo.fetch_etf_data(ticker="SPY", start_date=datetime(2022, 1, 1), end_date=datetime(2024, 1, 10))
    print(etf_data[1000].date)

        
