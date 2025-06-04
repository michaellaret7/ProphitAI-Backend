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

if __name__ == '__main__':
    # Example usage
    print("Available portfolios:")
    portfolios = get_available_portfolios()
    if portfolios is not None and not portfolios.empty:
        print(portfolios)
        
        # Test retrieving by name
        print("\n" + "="*50)
        portfolio_name = "gpt4_1minPortfolio"  # Example from your screenshot
        portfolio_df = retrieve_portfolio_information_from_db(portfolio_name, "name")
        if portfolio_df is not None and not portfolio_df.empty:
            print(f"\nData for portfolio '{portfolio_name}':")
            print(portfolio_df[['ticker', 'allocation']].head())
        
        # Test retrieving by ID
        print("\n" + "="*50)
        portfolio_id = 1  # Example ID
        portfolio_df = retrieve_portfolio_information_from_db(portfolio_id, "id")
        if portfolio_df is not None and not portfolio_df.empty:
            print(f"\nData for portfolio ID {portfolio_id}:")
            print(portfolio_df[['ticker', 'allocation']].head())
