from typing import List, Optional
from backend.src.repositories.base_repository import BaseRepository
from backend.src.data_models.user_models import UserPortfolioHoldings

# class UserCurrentPortfolioRepository:
#     """Minimalistic and efficient repository for portfolio data queries."""
#     def __init__(self):
#         pass
    
#     def fetch_holdings(self, email: str) -> List[UserPortfolioHoldings]:
#         """
#         Fetch user portfolio holdings by email.
#         Args:
#             email: User email address
#         Returns:
#             List of UserPortfolioHolding objects with validated data
#         """
#         conn = get_connection("user_data")
#         if not conn:
#             return []
        
#         try:
#             with conn.cursor(cursor_factory=RealDictCursor) as cursor:
#                 cursor.execute("""
#                     SELECT * FROM public.user_portfolios
#                     WHERE email = %s
#                 """, (email,))
                
#                 rows = cursor.fetchall()
                
#                 # Convert to Pydantic objects with validation
#                 holdings = []
#                 for row in rows:
#                     try:
#                         holding = UserPortfolioHoldings(**dict(row))
#                         holdings.append(holding)
#                     except Exception as e:
#                         print(f"Error validating holding data: {e}")
#                         print(f"Raw data: {dict(row)}")
#                         # Skip invalid records
#                         continue
                
#                 return holdings
            
#         except psycopg2.Error as e:
#             print(f"Query execution error: {e}")
#             return []
#         finally:
#             conn.close()


class UserCurrentPortfolioRepository(BaseRepository):
    """Minimalistic and efficient repository for portfolio data queries."""
    
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
        
        return self._execute_query_with_model_validation(
            db_name="user_data",
            query="SELECT * FROM public.user_portfolios WHERE user_id = %s OR email = %s",
            model_class=UserPortfolioHoldings,
            params=(user_id, email),
            fetch_one=False,  # Returns a list
            use_validation=True  # Uses try/catch validation like your original code
        )


if __name__ == "__main__":
    repo = UserCurrentPortfolioRepository()
    holdings = repo.fetch_holdings(user_id="user_01JXG39MMAVW1P3XVGX7YHN2DT")
    print(holdings[0].symbol)
