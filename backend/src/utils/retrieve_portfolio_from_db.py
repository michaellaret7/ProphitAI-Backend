import psycopg2
from psycopg2 import sql
import pandas as pd
from backend.src.utils.database import get_cursor

def retrieve_portfolio_information_from_db(schema_name: str, table_name: str):
    """
    Retrieves the final_portfolio information from the database for a given schema.

    Args:
        schema_name (str): The name of the schema (e.g., 'portfolio_one').

    Returns:
        pd.DataFrame: A Pandas DataFrame representing the final_portfolio table,
                      or None if an error occurs or no data is found.
    """
    db_name = "portfolio_results"

    query = sql.SQL("SELECT * FROM {}.{}").format(
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
    # Example usage (ensure your environment variables for DB connection are set)
    # And that you have a schema named 'portfolio_three' with a 'final_portfolio' table
    
    test_schema = "portfolio_five" 
    # table_name = "final_portfolio"
    # portfolio_df = retrieve_portfolio_information_from_db(test_schema, table_name)
    # if portfolio_df is not None and not portfolio_df.empty:
    #     print(f"Data from {test_schema}.final_portfolio:")
    #     print(portfolio_df)
    # elif portfolio_df is not None and portfolio_df.empty:
    #     print(f"No data found in {test_schema}.final_portfolio.")
    # else:
    #     print(f"Could not retrieve data for schema {test_schema}")
    # pass
