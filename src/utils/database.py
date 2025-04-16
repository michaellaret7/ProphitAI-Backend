"""
Database utilities for connection management and common operations.
"""
import os
import psycopg2
from contextlib import contextmanager

def get_default_db_config():
    """
    Get default database configuration from environment variables.
    
    Returns:
        dict: Database configuration parameters
    """
    return {
        "host": os.environ.get("DB_HOST"),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "port": os.environ.get("DB_PORT")
    }

@contextmanager
def get_db_connection(dbname=None, db_config=None):
    """
    Context manager for database connections.
    
    Usage:
        with get_db_connection(dbname="my_database") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM my_table")
            results = cursor.fetchall()
    
    Args:
        dbname: Database name to connect to
        db_config: Database configuration parameters
        
    Yields:
        psycopg2 connection object
    """
    # Use provided config or get default
    config = db_config if db_config is not None else get_default_db_config()
    
    # Add dbname if provided
    if dbname:
        config["dbname"] = dbname
    
    conn = None
    try:
        conn = psycopg2.connect(**config)
        yield conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise
    finally:
        if conn is not None:
            conn.close()

@contextmanager
def get_cursor(dbname=None, db_config=None):
    """
    Context manager for database cursors.
    
    Usage:
        with get_cursor(dbname="my_database") as cursor:
            cursor.execute("SELECT * FROM my_table")
            results = cursor.fetchall()
    
    Args:
        dbname: Database name to connect to
        db_config: Database configuration parameters
        
    Yields:
        psycopg2 cursor object
    """
    with get_db_connection(dbname, db_config) as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close() 