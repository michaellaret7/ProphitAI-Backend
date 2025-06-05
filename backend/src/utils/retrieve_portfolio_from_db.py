import psycopg2
from psycopg2 import sql
import pandas as pd
from typing import Optional, Union
from backend.src.utils.database import get_cursor

def retrieve_portfolio_information_from_db(portfolio_identifier: Union[str, int], identifier_type: str = "name") -> Optional[pd.DataFrame]:
    """
    Retrieves portfolio information from the database using either portfolio name or portfolio ID.

    Args:
        portfolio_identifier (Union[str, int]): The portfolio name (str) or portfolio ID (int) to retrieve.
        identifier_type (str): Either "name" to search by portfolio_name or "id" to search by portfolio_id.
                              Defaults to "name".

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the portfolio data (ticker, allocation, etc.),
                      or None if an error occurs or no data is found.
    """
    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "final_portfolio"

    # Build the query based on identifier type
    if identifier_type.lower() == "name":
        query = sql.SQL("SELECT * FROM {}.{} WHERE portfolio_name = %s").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name)
        )
        query_param = str(portfolio_identifier)
    elif identifier_type.lower() == "id":
        query = sql.SQL("SELECT * FROM {}.{} WHERE portfolio_id = %s").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name)
        )
        query_param = portfolio_identifier
    else:
        print(f"Invalid identifier_type: {identifier_type}. Use 'name' or 'id'.")
        return None

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, (query_param,))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for portfolio {identifier_type}: {portfolio_identifier}")
                return df
            else:
                print(f"ℹ️ No data found for portfolio {identifier_type}: {portfolio_identifier}")
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_available_portfolios() -> Optional[pd.DataFrame]:
    """
    Retrieves a list of available portfolios (portfolio_id, portfolio_name, user_name).
    
    Returns:
        pd.DataFrame: DataFrame containing unique portfolio information,
                      or None if an error occurs.
    """
    db_name = "portfolio_results"
    schema_name = "public"
    table_name = "final_portfolio"
    
    query = sql.SQL("SELECT DISTINCT portfolio_id, portfolio_name, user_name FROM {}.{} ORDER BY portfolio_id").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name)
    )
    
    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                return pd.DataFrame(results, columns=colnames)
            else:
                return pd.DataFrame()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def retrieve_user_current_portfolio_from_db(identifier: Union[str, int], identifier_type: str = "name") -> Optional[pd.DataFrame]:
    """
    Retrieves the current portfolio for a user from the database using user_name or pk_id (portfolio_id).

    Args:
        identifier (Union[str, int]): The user_name (str) or pk_id (int) to retrieve.
        identifier_type (str): Either "name" to search by user_name or "id" to search by pk_id.
                              Defaults to "name".

    Returns:
        pd.DataFrame: A Pandas DataFrame containing the user's current portfolio data,
                      or None if an error occurs or no data is found.
    """
    db_name = "user_data"  # Database name changed
    schema_name = "public"
    table_name = "user_portfolios"  # Table name changed

    # Build the query based on identifier type
    if identifier_type.lower() == "name":
        # Assuming 'user_name' is the column to filter by for names
        query = sql.SQL("SELECT * FROM {}.{} WHERE user_name = %s").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name)
        )
        query_param = str(identifier)
    elif identifier_type.lower() == "id":
        # Assuming 'pk_id' is the column for portfolio ID in user_portfolios table
        query = sql.SQL("SELECT * FROM {}.{} WHERE user_id = %s").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name)
        )
        query_param = identifier
    else:
        print(f"Invalid identifier_type: {identifier_type}. Use 'name' or 'id'.")
        return None

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, (query_param,))
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            if results:
                df = pd.DataFrame(results, columns=colnames)
                print(f"✅ Retrieved {len(df)} records for user portfolio {identifier_type}: {identifier}")
                return df
            else:
                print(f"ℹ️ No data found for user portfolio {identifier_type}: {identifier}")
                return pd.DataFrame() # Return empty DataFrame if no data
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    # Example usage
    print("Available portfolios:")
    portfolios = get_available_portfolios()
    if portfolios is not None and not portfolios.empty:
        # print(portfolios)
        
        # # Test retrieving by name
        # print("\n" + "="*50)
        # portfolio_name = "gpt4_1minPortfolio"  # Example from your screenshot
        # portfolio_df = retrieve_portfolio_information_from_db(portfolio_name, "name")
        # if portfolio_df is not None and not portfolio_df.empty:
        #     print(f"\nData for portfolio '{portfolio_name}':")
        #     print(portfolio_df[['ticker', 'allocation']].head())
        
        # # Test retrieving by ID
        # print("\n" + "="*50)
        # portfolio_id = 1  # Example ID
        # portfolio_df = retrieve_portfolio_information_from_db(portfolio_id, "id")
        # if portfolio_df is not None and not portfolio_df.empty:
        #     print(f"\nData for portfolio ID {portfolio_id}:")
        #     print(portfolio_df[['ticker', 'allocation']].head())

        # Test retrieving user's current portfolio by user_name
        print("\n" + "="*50)
        user_name_to_test = "test_user_beta" # Example from your screenshot
        user_portfolio_df = retrieve_user_current_portfolio_from_db(user_name_to_test, "name")
        if user_portfolio_df is not None and not user_portfolio_df.empty:
            print(f"\nData for user '{user_name_to_test}':")
            print(f"Columns in user_portfolio_df: {user_portfolio_df.columns.tolist()}")
            # Display relevant columns, e.g., symbol, position, marketprice
            # Adjust columns based on the 'user_portfolios' table structure from your screenshot
            print(user_portfolio_df[['symbol', 'position', 'marketprice', 'marketvalue']].head())
        elif user_portfolio_df is not None:
             print(f"No portfolio data found for user '{user_name_to_test}'.")

        print("\n" + "="*50)
        example_pk_id = "2594bb4d-784c-4c53-a049-8438baaf0d7c" # Replace with an actual pk_id from your table
        user_portfolio_by_id_df = retrieve_user_current_portfolio_from_db(example_pk_id, "id")
        print(user_portfolio_by_id_df)