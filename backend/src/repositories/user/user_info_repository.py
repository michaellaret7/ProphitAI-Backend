from typing import List, Optional
from backend.src.data_models.user_models import UserInfo
from backend.src.repositories.base_repository import BaseRepository

# class UserInfoRepository:
#     def __init__(self):
#         pass
    
#     def fetch_user_by_email(self, email: str) -> Optional[UserInfo]:
#         """
#         Fetch user information by email address.
#         Args:
#             email: User email address
#         Returns:
#             UserInfo object if found, None otherwise
#         """
#         conn = get_connection("user_data")
#         if not conn:
#             return None

#         try:
#             with conn.cursor(cursor_factory=RealDictCursor) as cursor:
#                 cursor.execute("""
#                     SELECT * FROM public.users
#                     WHERE email = %s
#                 """, (email,))
                
#                 row = cursor.fetchone()
#                 if not row:
#                     return None
                
#                 try:
#                     return UserInfo(**dict(row))
#                 except Exception as e:
#                     print(f"Error validating user data: {e}")
#                     print(f"Raw data: {dict(row)}")
#                     return None
            
#         except psycopg2.Error as e:
#             print(f"Query execution error: {e}")
#             return None
#         finally:
#             conn.close()
    
#     def fetch_user_by_id(self, user_id: str) -> Optional[UserInfo]:
#         """
#         Fetch user information by user ID.
#         Args:
#             user_id: User ID string
#         Returns:
#             UserInfo object if found, None otherwise
#         """
#         conn = get_connection("user_data")
#         if not conn:
#             return None
        
#         try:
#             with conn.cursor(cursor_factory=RealDictCursor) as cursor:
#                 cursor.execute("""
#                     SELECT * FROM public.users
#                     WHERE id = %s
#                 """, (user_id,))
                
#                 row = cursor.fetchone()
#                 if not row:
#                     return None
                
#                 try:
#                     return UserInfo(**dict(row))
#                 except Exception as e:
#                     print(f"Error validating user data: {e}")
#                     print(f"Raw data: {dict(row)}")
#                     return None
            
#         except psycopg2.Error as e:
#             print(f"Query execution error: {e}")
#             return None
#         finally:
#             conn.close()


class UserInfoRepository(BaseRepository):
    """Repository for user account information."""
    
    def fetch_user_by_email(self, email: str) -> Optional[UserInfo]:
        """
        Fetch user information by email address.
        Args:
            email: User email address
        Returns:
            UserInfo object if found, None otherwise
        """
        return self._execute_query_with_model_validation(
            db_name="user_data",
            query="SELECT * FROM public.users WHERE email = %s",
            model_class=UserInfo,
            params=(email,),
            fetch_one=True,
            use_validation=True
        )
    
    def fetch_user_by_id(self, user_id: str) -> Optional[UserInfo]:
        """
        Fetch user information by user ID.
        Args:
            user_id: User ID string
        Returns:
            UserInfo object if found, None otherwise
        """
        return self._execute_query_with_model_validation(
            db_name="user_data",
            query="SELECT * FROM public.users WHERE id = %s", 
            model_class=UserInfo,
            params=(user_id,),
            fetch_one=True,
            use_validation=True
        )

if __name__ == "__main__":
    repo = UserInfoRepository()
    user = repo.fetch_user_by_email("michael@laret.com")
    print(user)