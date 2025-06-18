"""
Database utilities for connection management and common operations.
"""
import os
import psycopg2
from contextlib import contextmanager
from typing import Optional, Dict, Tuple, Any, List
from psycopg2.extras import execute_values

# Connection pool to reuse database connections
_connection_pool: Dict[str, psycopg2.extensions.connection] = {}

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

def get_connection(dbname: str, db_config: Optional[Dict] = None) -> Optional[psycopg2.extensions.connection]:
    """
    Get a simple database connection with proper error handling.
    
    Args:
        dbname: Database name to connect to
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        psycopg2 connection object or None if error
    """
    # Use provided config or get default
    config = db_config if db_config is not None else get_default_db_config()
    
    try:
        config['dbname'] = dbname
        return psycopg2.connect(**config)
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_pooled_connection(dbname: str, db_config: Optional[Dict] = None, autocommit: bool = False) -> Tuple[Optional[psycopg2.extensions.connection], Optional[psycopg2.extensions.cursor]]:
    """
    Get a database connection from the pool or create a new one.
    
    Args:
        dbname: Database name to connect to
        db_config: Database configuration parameters (uses default if None)
        autocommit: Whether to enable autocommit mode
        
    Returns:
        Tuple of (connection, cursor) or (None, None) if error
    """
    # Use provided config or get default
    config = db_config if db_config is not None else get_default_db_config()
    
    # Check if we have a connection in our pool that we can reuse
    pool_key = f"{dbname}_{autocommit}"
    if pool_key in _connection_pool and _connection_pool[pool_key] is not None:
        try:
            # Test if the connection is still good with a simple query
            cursor = _connection_pool[pool_key].cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return _connection_pool[pool_key], _connection_pool[pool_key].cursor()
        except psycopg2.Error:
            # If connection is broken, close it and create a new one
            try:
                _connection_pool[pool_key].close()
            except:
                pass
            _connection_pool[pool_key] = None
    
    # Create a new connection if needed
    try:
        config['dbname'] = dbname
        conn = psycopg2.connect(**config)
        conn.autocommit = autocommit
        cursor = conn.cursor()
        
        # Store in connection pool for reuse
        _connection_pool[pool_key] = conn
        return conn, cursor
    except psycopg2.Error as e:
        print(f"Error connecting to database {dbname}: {e}")
        return None, None

def close_pooled_connection(dbname: Optional[str] = None, autocommit: bool = False):
    """
    Close pooled database connections.
    
    Args:
        dbname: Specific database to close, or None to close all
        autocommit: Whether the connection was in autocommit mode
    """
    if dbname:
        pool_key = f"{dbname}_{autocommit}"
        if pool_key in _connection_pool and _connection_pool[pool_key]:
            try:
                _connection_pool[pool_key].close()
                _connection_pool[pool_key] = None
            except Exception as e:
                print(f"Error closing connection to {dbname}: {e}")
    else:
        # Close all connections
        for key, conn in list(_connection_pool.items()):
            if conn:
                try:
                    conn.close()
                    _connection_pool[key] = None
                except Exception as e:
                    print(f"Error closing connection {key}: {e}")

def create_database(db_name: str, db_config: Optional[Dict] = None) -> bool:
    """
    Create a database if it doesn't exist.
    
    Args:
        db_name: Name of the database to create
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        bool: True if successful or database already exists, False if error
    """
    config = db_config if db_config is not None else get_default_db_config()
    conn = None
    cursor = None
    
    try:
        # Connect to postgres database to create new database
        config['dbname'] = 'postgres'
        conn = psycopg2.connect(**config)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")
        
        return True
    except Exception as e:
        print(f"Error in create_database: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@contextmanager
def get_db_connection(dbname: str, db_config: Optional[Dict] = None):
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
        print(f"Failed to get DB connection for {dbname}: {e}")
        return None
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

def table_exists(dbname: str, schema: str, table: str, db_config: Optional[Dict] = None) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        dbname: Database name
        schema: Schema name
        table: Table name
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        with get_cursor(dbname, db_config) as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = %s 
                    AND table_name = %s
                )
            """, (schema, table))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error checking if table {schema}.{table} exists: {e}")
        return False

def create_schema(dbname: str, schema: str, db_config: Optional[Dict] = None) -> bool:
    """
    Create a schema if it doesn't exist.
    
    Args:
        dbname: Database name
        schema: Schema name to create
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        bool: True if successful or schema already exists, False otherwise
    """
    try:
        with get_db_connection(dbname, db_config) as conn:
            cursor = conn.cursor()
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            conn.commit()
            return True
    except Exception as e:
        print(f"Error creating schema {schema}: {e}")
        return False

def execute_bulk_insert(dbname: str, query: str, data: list, 
                       page_size: int = 1000, db_config: Optional[Dict] = None) -> bool:
    """
    Execute bulk insert using psycopg2.extras.execute_values.
    
    Args:
        dbname: Database name
        query: INSERT query with VALUES %s placeholder
        data: List of tuples to insert
        page_size: Number of rows per batch
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        bool: True if successful, False otherwise
    """
    from psycopg2.extras import execute_values
    
    try:
        with get_db_connection(dbname, db_config) as conn:
            cursor = conn.cursor()
            execute_values(cursor, query, data, page_size=page_size)
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"Error during bulk insert: {e}")
        return False

def get_single_value(dbname: str, query: str, params: Optional[tuple] = None, 
                    db_config: Optional[Dict] = None) -> Optional[Any]:
    """
    Execute a query and return a single value result.
    
    Args:
        dbname: Database name
        query: SQL query to execute
        params: Query parameters
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        The single value result or None if no results or error
    """
    try:
        with get_cursor(dbname, db_config) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

def execute_query(dbname: str, query: str, params: Optional[tuple] = None,
                  db_config: Optional[Dict] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a query and return all results as a list of dictionaries.
    
    Args:
        dbname: Database name
        query: SQL query to execute
        params: Optional parameters for the query
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        List of dictionaries with results or None if error
    """
    try:
        with get_db_connection(dbname, db_config) as conn:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
    except Exception as e:
        print(f"Database error: {e}")
        return None

def execute_ddl(dbname: str, query: str, db_config: Optional[Dict] = None) -> bool:
    """
    Execute a DDL query, for creating schemas and tables.
    
    Args:
        dbname: Database name
        query: DDL query to execute
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db_connection(dbname, db_config) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            cursor.close()
            return True
    except psycopg2.Error as e:
        if "already exists" in str(e):
            print(f"Notice: {e}")
            conn.rollback()
            return True
        print(f"Error executing DDL query '{query}': {e}")
        conn.rollback()
        return False

def get_table_columns(dbname: str, table_name: str, schema: str = 'public',
                      db_config: Optional[Dict] = None) -> Optional[List[Tuple[str, str]]]:
    """
    Get table columns and their data types from the database.
    
    Args:
        dbname: Database name
        table_name: Table name
        schema: Schema name (default is 'public')
        db_config: Database configuration parameters (uses default if None)
        
    Returns:
        List of tuples (column_name, data_type) or None if error
    """
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s
        AND table_name = %s
    """
    try:
        with get_db_connection(dbname, db_config) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (schema, table_name))
            columns = cursor.fetchall()
            cursor.close()
            return columns
    except Exception as e:
        print(f"Error fetching columns for {schema}.{table_name}: {e}")
        return None 