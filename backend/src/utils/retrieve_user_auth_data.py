from typing import Optional
from backend.src.utils.database import get_single_value

def get_user_id_from_email(email: str) -> Optional[str]:
    """
    Retrieves a user's ID from the database based on their email address.

    Args:
        email: The email address of the user to look up.

    Returns:
        The user's ID as a string if found, otherwise None.
    """
    db_name = 'user_data'
    query = "SELECT id FROM public.users WHERE email = %s"
    params = (email,)
    
    user_id = get_single_value(dbname=db_name, query=query, params=params)
    
    if user_id is not None:
        return str(user_id)
    return None


if __name__ == "__main__":
    print(get_user_id_from_email('michael@laret.com'))