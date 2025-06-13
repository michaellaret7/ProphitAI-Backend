import psycopg2
from psycopg2 import sql
import pandas as pd
from typing import Optional, Union
from backend.src.utils.database import get_cursor

# THIS RETRIEVES THE OPTIMIZED/BUILT PORTFOLIOS FROM THE DATABASE
def retrieve_built_portfolio_from_db(portfolio_id: str, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Retrieves portfolio information from the database using portfolio ID and either user_id or email.

    Args:
        portfolio_id (str): The portfolio ID to retrieve.
        user_id (Optional[str]): The user ID associated with the portfolio.
        email (Optional[str]): The email associated with the portfolio.

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the portfolio data (ticker, allocation, etc.),
                      or None if an error occurs or no data is found.
    """
    if not user_id and not email:
        print("Either user_id or email must be provided.")
        return None

    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "final_portfolio"

    # Build the query
    base_query = "SELECT * FROM {}.{} WHERE portfolio_id = %s"
    params = [portfolio_id]

    identifier_log = f"portfolio_id: {portfolio_id}"
    if user_id:
        base_query += " AND user_id = %s"
        params.append(user_id)
        identifier_log += f", user_id: {user_id}"
    elif email:
        base_query += " AND email = %s"
        params.append(email)
        identifier_log += f", email: {email}"

    query = sql.SQL(base_query).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )
    
    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for {identifier_log}")
                return df
            else:
                print(f"ℹ️ No data found for {identifier_log}")
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# THIS RETRIEVES THE OPTIMIZED/BUILT ALLOCATIONS FROM THE DATABASE
def get_portfolio_allocations(portfolio_id: str, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Retrieves portfolio sector allocations from the database using portfolio ID and either user_id or email.

    Args:
        portfolio_id (str): The portfolio ID to retrieve allocations for.
        user_id (Optional[str]): The user ID associated with the portfolio.
        email (Optional[str]): The email associated with the portfolio.

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the portfolio allocation data,
                      or None if an error occurs or no data is found.
    """
    if not user_id and not email:
        print("Either user_id or email must be provided.")
        return None

    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "portfolio_sector_allocation"

    # Build the query
    base_query = "SELECT * FROM {}.{} WHERE portfolio_id = %s"
    params = [portfolio_id]

    identifier_log = f"portfolio_id: {portfolio_id}"
    if user_id:
        base_query += " AND user_id = %s"
        params.append(user_id)
        identifier_log += f", user_id: {user_id}"
    elif email:
        base_query += " AND email = %s"
        params.append(email)
        identifier_log += f", email: {email}"

    query = sql.SQL(base_query).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for portfolio allocations for {identifier_log}")
                return df
            else:
                print(f"ℹ️ No data found for portfolio allocations for {identifier_log}")
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# THIS RETRIEVES THE OPTIMIZED/BUILT PORTFOLIOS FROM THE DATABASE
def get_available_portfolios(user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Retrieves a list of available portfolios, optionally filtered by user_id or email.

    Args:
        user_id (Optional[str]): The user ID to filter portfolios by.
        email (Optional[str]): The email to filter portfolios by.

    Returns:
        pd.DataFrame: DataFrame containing portfolio information (portfolio_id, portfolio_name, user_id, email),
                      or None if an error occurs.
    """
    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "portfolios"
    
    base_query = "SELECT portfolio_id, portfolio_name, user_id, email, created_at FROM {}.{}"
    params = []
    
    filter_clauses = []
    if user_id:
        filter_clauses.append("user_id = %s")
        params.append(user_id)
    if email:
        filter_clauses.append("email = %s")
        params.append(email)

    if filter_clauses:
        base_query += " WHERE " + " AND ".join(filter_clauses)
        
    base_query += " ORDER BY created_at DESC"

    query = sql.SQL(base_query).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )
    
    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                return pd.DataFrame(results, columns=colnames)
            else:
                return pd.DataFrame(columns=colnames)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# THIS RETRIEVES THE OPTIMIZED/BUILT PORTFOLIO THESES FROM THE DATABASE
def get_portfolio_thesis(portfolio_id: str, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Retrieves portfolio thesis from the database using portfolio ID and either user_id or email.

    Args:
        portfolio_id (str): The portfolio ID to retrieve the thesis for.
        user_id (Optional[str]): The user ID associated with the portfolio.
        email (Optional[str]): The email associated with the portfolio.

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the portfolio thesis data,
                      or None if an error occurs or no data is found.
    """
    if not user_id and not email:
        print("Either user_id or email must be provided.")
        return None

    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "portfolio_thesis"

    base_query = "SELECT * FROM {}.{} WHERE portfolio_id = %s"
    params = [portfolio_id]

    identifier_log = f"portfolio_id: {portfolio_id}"
    if user_id:
        base_query += " AND user_id = %s"
        params.append(user_id)
        identifier_log += f", user_id: {user_id}"
    elif email:
        base_query += " AND email = %s"
        params.append(email)
        identifier_log += f", email: {email}"

    query = sql.SQL(base_query).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for portfolio thesis for {identifier_log}")
                return df
            else:
                print(f"ℹ️ No data found for portfolio thesis for {identifier_log}")
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# THIS RETRIEVES THE USER INFORMATION FROM THE DATABASE WHICH IS FROM THE OPTIMIZED/BUILT PORTFOLIOS
def get_user_information_from_db(portfolio_id: str, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Retrieves user information from the database using portfolio ID and either user_id or email.

    Args:
        portfolio_id (str): The portfolio ID to retrieve user information for.
        user_id (Optional[str]): The user ID associated with the portfolio.
        email (Optional[str]): The email associated with the portfolio.

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the user information,
                      or None if an error occurs or no data is found.
    """
    if not user_id and not email:
        print("Either user_id or email must be provided.")
        return None

    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "user_information"

    base_query = "SELECT * FROM {}.{} WHERE portfolio_id = %s"
    params = [portfolio_id]

    identifier_log = f"portfolio_id: {portfolio_id}"
    if user_id:
        base_query += " AND user_id = %s"
        params.append(user_id)
        identifier_log += f", user_id: {user_id}"
    elif email:
        base_query += " AND email = %s"
        params.append(email)
        identifier_log += f", email: {email}"

    query = sql.SQL(base_query).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for user information for {identifier_log}")
                return df
            else:
                print(f"ℹ️ No data found for user information for {identifier_log}")
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# THIS RETRIEVES THE USERS CURRENT PORTFOLIO FROM THE DATABASE
def retrieve_user_current_portfolio_from_db(user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Retrieves the current portfolio for a user from the 'user_data' database using user_id and/or email.

    Args:
        user_id (Optional[str]): The user ID to retrieve the portfolio for.
        email (Optional[str]): The email to retrieve the portfolio for.

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the user's current portfolio data,
                      or None if an error occurs or no data is found.
    """
    if not user_id and not email:
        print("Either user_id or email must be provided.")
        return None

    db_name = "user_data"
    schema_name = "public"
    table_name = "user_portfolios"

    base_query = "SELECT * FROM {}.{}"
    params = []
    
    filter_clauses = []
    identifier_log_parts = []
    if user_id:
        filter_clauses.append("user_id = %s")
        params.append(user_id)
        identifier_log_parts.append(f"user_id: {user_id}")
    if email:
        filter_clauses.append("email = %s")
        params.append(email)
        identifier_log_parts.append(f"email: {email}")

    if filter_clauses:
        base_query += " WHERE " + " AND ".join(filter_clauses)
    
    identifier_log = ", ".join(identifier_log_parts)

    query = sql.SQL(base_query).format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for user portfolio for {identifier_log}")
                return df
            else:
                print(f"ℹ️ No data found for user portfolio for {identifier_log}")
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    # Example usage
    print("Available portfolios:")
    # print(get_portfolio_allocations(portfolio_id="839049b7-1ae8-4ef5-a27a-af8dcf4577e3", email="michael@laret.com"))
    # print(get_portfolio_thesis(portfolio_id="839049b7-1ae8-4ef5-a27a-af8dcf4577e3", email="michael@laret.com"))
    print(get_user_information_from_db(portfolio_id="839049b7-1ae8-4ef5-a27a-af8dcf4577e3", email="michael@laret.com"))
    print(get_portfolio_thesis(portfolio_id="839049b7-1ae8-4ef5-a27a-af8dcf4577e3", email="michael@laret.com"))

         