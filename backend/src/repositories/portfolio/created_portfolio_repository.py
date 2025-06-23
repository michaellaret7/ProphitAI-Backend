from typing import List, Optional
from uuid import UUID
from backend.src.data_models.portfolio_models import (
    UserCreatedPortfolio, 
    UserCreatedPortfolioAllocations, 
    UserCreatedPortfolioThesis,
    UserCreatedAvailablePortfolios,
    UserCreatedInvestmentInformation
)
from backend.src.utils.database import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

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
    
    def fetch_portfolio_allocations(self, portfolio_id: UUID, user_id: Optional[str] = None, email: Optional[str] = None) -> List[UserCreatedPortfolioAllocations]:
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
                return [UserCreatedPortfolioAllocations(**dict(row)) for row in rows]
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return []
        finally:
            conn.close()
    
    def fetch_portfolio_thesis(self, portfolio_id: UUID, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[UserCreatedPortfolioThesis]:
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
                    return UserCreatedPortfolioThesis(**dict(row))
                return None
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()
    
    def fetch_available_portfolios(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[UserCreatedAvailablePortfolios]:
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
                return [UserCreatedAvailablePortfolios(**dict(row)) for row in rows]
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return []
        finally:
            conn.close()
    
    def fetch_user_investment_information(self, portfolio_id: UUID) -> Optional[UserCreatedInvestmentInformation]:
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
                    return UserCreatedInvestmentInformation(**dict(row))
                return None
            
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()



