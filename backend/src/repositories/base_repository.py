import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Any, Callable, TypeVar, Union
from backend.src.utils.database import get_connection

T = TypeVar('T')

class BaseRepository:
    """Base repository class with common database operations and error handling."""
    
    def __init__(self):
        pass
    
    def _execute_query_with_model_validation(
        self,
        db_name: str,
        query: str,
        model_class: Callable[[Dict], T],
        params: tuple = (),
        fetch_one: bool = False,
        use_validation: bool = True
    ) -> Union[Optional[List[T]], Optional[T]]:
        """
        Execute query and optionally validate results with Pydantic models.
        
        Args:
            db_name: Database connection name
            query: SQL query string
            model_class: Pydantic model class for validation
            params: Query parameters tuple
            fetch_one: Return single model instance if True
            use_validation: Whether to use try/catch validation (user pattern vs portfolio pattern)
            
        Returns:
            List of validated model instances, single instance, or None/[]
        """
        conn = get_connection(db_name)
        if not conn:
            return None if fetch_one else []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                if fetch_one:
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    if use_validation:
                        try:
                            return model_class(**dict(row))
                        except Exception as e:
                            print(f"Error validating model data: {e}")
                            print(f"Raw data: {dict(row)}")
                            return None
                    else:
                        return model_class(**dict(row))
                else:
                    rows = cursor.fetchall()
                    
                    if use_validation:
                        validated_objects = []
                        for row in rows:
                            try:
                                obj = model_class(**dict(row))
                                validated_objects.append(obj)
                            except Exception as e:
                                print(f"Error validating model data: {e}")
                                print(f"Raw data: {dict(row)}")
                                # Skip invalid records
                                continue
                        return validated_objects
                    else:
                        return [model_class(**dict(row)) for row in rows]
                    
        except psycopg2.Error as e:
            print(f"Query execution error: {e}")
            return None if fetch_one else []
        finally:
            conn.close()
    
    def _search_ticker_across_databases(
        self,
        ticker: str,
        database_list: List[str],
        start_date,
        end_date,
        model_class: Callable[[Dict], T]
    ) -> List[T]:
        """
        Search for ticker across multiple databases (equity pattern).
        """
        ticker_lower = ticker.lower()
        
        for db_name in database_list:
            conn = get_connection(db_name)
            if not conn:
                continue
                
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Find which schema contains the ticker table
                    cursor.execute("""
                        SELECT schemaname, tablename 
                        FROM pg_tables 
                        WHERE tablename = %s
                    """, (ticker_lower,))
                    
                    table_info = cursor.fetchone()
                    if table_info:
                        schema_name = table_info['schemaname']
                        
                        # Execute the actual data query
                        cursor.execute(f"""
                            SELECT date, open, high, low, close, volume
                            FROM {schema_name}.{ticker_lower}
                            WHERE date >= %s AND date <= %s
                            ORDER BY date
                        """, (start_date, end_date))
                        
                        rows = cursor.fetchall()
                        conn.close()  # Close early and return (matches your pattern)
                        return [model_class(**dict(row)) for row in rows]
                
            except psycopg2.Error as e:
                print(f"Error searching in {db_name}: {e}")
                continue
            finally:
                conn.close()
        
        print(f"Ticker '{ticker}' not found in any database")
        return []
    
    def _search_ticker_in_schemas(
        self,
        ticker: str,
        schema_list: List[str],
        start_date,
        end_date,
        model_class: Callable[[Dict], T],
        db_name: str = "etf_prices"
    ) -> List[T]:
        """
        Search for ticker across multiple schemas in one database (ETF pattern).
        """
        ticker_lower = ticker.lower()
        
        conn = get_connection(db_name)
        if not conn:
            print(f"Could not connect to {db_name} database")
            return []
            
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Search through each schema
                for schema_name in schema_list:
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = %s AND tablename = %s
                    """, (schema_name, ticker_lower))
                    
                    table_info = cursor.fetchone()
                    if table_info:
                        # Found the ticker, execute data query
                        cursor.execute(f"""
                            SELECT datetime as date, open, high, low, close, volume
                            FROM {schema_name}.{ticker_lower}
                            WHERE datetime >= %s AND datetime <= %s
                            ORDER BY datetime
                        """, (start_date, end_date))
                        
                        rows = cursor.fetchall()
                        return [model_class(**dict(row)) for row in rows]
                
                print(f"Ticker '{ticker}' not found in any {db_name} schema")
                return []
            
        except psycopg2.Error as e:
            print(f"Error searching in {db_name} database: {e}")
            return []
        finally:
            conn.close()