import psycopg2
from backend.src.utils.database import get_cursor



def delete_other_user_portfolios():
    """
    Deletes all rows from the user_portfolios table where the user_id is not '2594bb4d-784c-4c53-a049-8438baaf0d7c'.
    This function connects to the 'user_data' database.
    """
    db_name = "user_data"
    schema = "public"
    table_name = "user_portfolios"
    user_id_to_keep = "2594bb4d-784c-4c53-a049-8438baaf0d7c"
    
    sql_command = f"DELETE FROM {schema}.{table_name} WHERE user_id != %s;"
    
    print(f"Connecting to database '{db_name}' to clear irrelevant user portfolios...")
    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(sql_command, (user_id_to_keep,))
            print(f"Successfully deleted portfolios for users other than {user_id_to_keep}. Rows affected: {cursor.rowcount}")
    except psycopg2.Error as e:
        print(f"Database error during portfolio deletion: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def update_user_ids():
    """
    Updates all user_id rows in the user_portfolios table to a specific user_id.
    This function connects to the 'user_data' database.
    """
    db_name = "user_data"
    schema = "public"
    table_name = "user_portfolios"
    new_user_id = "user_01JXG39MMAVW1P3XVGX7YHN2DT"
    
    sql_command = f"UPDATE {schema}.{table_name} SET user_id = %s;"
    
    print(f"Connecting to database '{db_name}' to update user IDs in {schema}.{table_name}...")
    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(sql_command, (new_user_id,))
            print(f"Successfully updated all user IDs to '{new_user_id}'. Rows affected: {cursor.rowcount}")
    except psycopg2.Error as e:
        print(f"Database error during user ID update: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def update_portfolio_sector_allocation_user_id():
    """
    Adds a 'user_id' column to the 'portfolio_sector_allocation' table
    and populates it based on the 'portfolio_id'.
    """
    db_name = "portfolio_results"
    schema = "public"
    table_name = "portfolio_sector_allocation"
    specific_portfolio_id = "f0e3e97b-ff5c-48a2-93e9-d8a1fa84c75b"
    specific_user_id = "user_01JXG39MMAVW1P3XVGX7YHN2DT"
    default_user_id = "test1"

    add_column_sql = f"ALTER TABLE {schema}.{table_name} ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);"
    update_specific_user_sql = f"UPDATE {schema}.{table_name} SET user_id = %s WHERE portfolio_id = %s;"
    update_other_users_sql = f"UPDATE {schema}.{table_name} SET user_id = %s WHERE portfolio_id != %s;"

    print(f"Connecting to database '{db_name}' to modify {schema}.{table_name}...")
    try:
        with get_cursor(dbname=db_name) as cursor:
            # Add the user_id column if it doesn't exist
            print("Adding 'user_id' column if it does not exist...")
            cursor.execute(add_column_sql)
            print("'user_id' column check/add complete.")

            # Update the user_id for the specific portfolio_id
            print(f"Updating user_id for portfolio_id {specific_portfolio_id}...")
            cursor.execute(update_specific_user_sql, (specific_user_id, specific_portfolio_id))
            print(f"Rows affected: {cursor.rowcount}")

            # Update the user_id for all other portfolio_ids
            print("Updating user_id for all other portfolios...")
            cursor.execute(update_other_users_sql, (default_user_id, specific_portfolio_id))
            print(f"Rows affected: {cursor.rowcount}")

            print("Successfully updated user_ids in portfolio_sector_allocation.")

    except psycopg2.Error as e:
        print(f"Database error during portfolio_sector_allocation update: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def delete_user_name_column():
    """
    Deletes the 'user_name' column from the 'user_portfolios' table in the 'user_data' database.
    """
    db_name = "user_data"
    schema = "public"
    table_name = "user_portfolios"
    column_to_delete = "user_name"

    sql_command = f"ALTER TABLE {schema}.{table_name} DROP COLUMN IF EXISTS {column_to_delete};"

    print(f"Connecting to database '{db_name}' to delete column '{column_to_delete}' from {schema}.{table_name}...")
    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(sql_command)
            print(f"Successfully deleted column '{column_to_delete}' from {schema}.{table_name}.")
    except psycopg2.Error as e:
        print(f"Database error during column deletion: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def add_email_to_user_portfolios():
    """
    Adds an 'email' column to the 'user_portfolios' table and sets a default email.
    """
    db_name = "user_data"
    schema = "public"
    table_name = "user_portfolios"
    new_column_name = "email"
    default_email = "michael@laret.com"

    add_column_sql = f"ALTER TABLE {schema}.{table_name} ADD COLUMN IF NOT EXISTS {new_column_name} VARCHAR(255);"
    update_email_sql = f"UPDATE {schema}.{table_name} SET {new_column_name} = %s;"

    print(f"Connecting to database '{db_name}' to modify {schema}.{table_name}...")
    try:
        with get_cursor(dbname=db_name) as cursor:
            # Add the email column if it doesn't exist
            print(f"Adding '{new_column_name}' column if it does not exist...")
            cursor.execute(add_column_sql)
            print(f"'{new_column_name}' column check/add complete.")

            # Update the email for all rows
            print(f"Updating {new_column_name} for all users...")
            cursor.execute(update_email_sql, (default_email,))
            print(f"Rows affected: {cursor.rowcount}")

            print(f"Successfully added and populated '{new_column_name}' column in {table_name}.")

    except psycopg2.Error as e:
        print(f"Database error during email column addition/update: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def update_portfolio_results_tables_for_workos():
    """
    Updates several tables in the 'portfolio_results' database to align with WorkOS user data.
    This includes deleting 'user_name' column, adding 'user_id' and 'email' columns if they don't exist,
    and populating them with specific values.
    """
    db_name = "portfolio_results"
    schema = "public"
    tables = [
        "final_portfolio",
        "portfolio_sector_allocation",
        "portfolio_thesis",
        "portfolios",
        "user_information"
    ]
    new_user_id = "user_01JXG39MMAVW1P3XVGX7YHN2DT"
    new_email = "michael@laret.com"
    column_to_delete = "user_name"
    user_id_column = "user_id"
    email_column = "email"

    print(f"Connecting to database '{db_name}' to update tables for WorkOS integration...")
    try:
        with get_cursor(dbname=db_name) as cursor:
            for table_name in tables:
                print(f"--- Processing table: {schema}.{table_name} ---")

                # Delete the user_name column
                print(f"Deleting column '{column_to_delete}' if it exists...")
                delete_column_sql = f"ALTER TABLE {schema}.{table_name} DROP COLUMN IF EXISTS {column_to_delete};"
                cursor.execute(delete_column_sql)
                print(f"Column '{column_to_delete}' deleted or did not exist.")

                # Add the user_id column if it doesn't exist
                print(f"Adding '{user_id_column}' column if it does not exist...")
                add_user_id_sql = f"ALTER TABLE {schema}.{table_name} ADD COLUMN IF NOT EXISTS {user_id_column} VARCHAR(255);"
                cursor.execute(add_user_id_sql)
                print(f"'{user_id_column}' column check/add complete.")

                # Add the email column if it doesn't exist
                print(f"Adding '{email_column}' column if it does not exist...")
                add_email_sql = f"ALTER TABLE {schema}.{table_name} ADD COLUMN IF NOT EXISTS {email_column} VARCHAR(255);"
                cursor.execute(add_email_sql)
                print(f"'{email_column}' column check/add complete.")

                # Update the user_id for all rows
                print(f"Updating {user_id_column} for all rows...")
                update_user_id_sql = f"UPDATE {schema}.{table_name} SET {user_id_column} = %s;"
                cursor.execute(update_user_id_sql, (new_user_id,))
                print(f"Rows affected: {cursor.rowcount}")

                # Update the email for all rows
                print(f"Updating {email_column} for all rows...")
                update_email_sql = f"UPDATE {schema}.{table_name} SET {email_column} = %s;"
                cursor.execute(update_email_sql, (new_email,))
                print(f"Rows affected: {cursor.rowcount}")
                
                print(f"--- Finished processing table: {schema}.{table_name} ---\n")

            print("Successfully updated all specified tables in 'portfolio_results'.")

    except psycopg2.Error as e:
        print(f"Database error during table updates: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # To run a function, uncomment the corresponding line:
    # delete_other_user_portfolios()
    # update_user_ids()
    # update_portfolio_sector_allocation_user_id()
    # delete_user_name_column()
    # add_email_to_user_portfolios()
    # update_portfolio_results_tables_for_workos()
    pass
    