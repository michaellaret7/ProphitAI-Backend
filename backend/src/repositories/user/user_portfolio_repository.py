from typing import List, Optional
from backend.src.repositories.base_repository import BaseRepository
from backend.src.data_models.user_models import UserPortfolioHoldings
from backend.src.utils.database import get_connection
from psycopg2.extras import RealDictCursor
import psycopg2

class UserCurrentPortfolioRepository:
    """Minimalistic and efficient repository for portfolio data queries."""
    def __init__(self):
        pass
    
    def fetch_holdings(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[UserPortfolioHoldings]:
        """
        Fetch user portfolio holdings by user_id and/or email.
        Args:
            user_id: User ID string (optional)
            email: User email address (optional)
        Returns:
            List of UserPortfolioHolding objects with validated data
        """
        if not user_id and not email:
            raise ValueError("Either user_id or email must be provided")

        conn = get_connection("user_data")
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query_conditions = []
                params = []
                if user_id:
                    query_conditions.append("user_id = %s")
                    params.append(user_id)
                if email:
                    query_conditions.append("email = %s")
                    params.append(email)
                
                query = "SELECT * FROM public.user_portfolios WHERE " + " OR ".join(query_conditions)
                
                cursor.execute(query, tuple(params))
                
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


