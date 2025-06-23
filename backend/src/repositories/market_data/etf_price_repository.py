from typing import List
from datetime import datetime
from backend.src.data_models.market_data_models import PriceData
from backend.src.utils.database import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

class ETFDataRepository:
    def __init__(self):
        pass
    
    def fetch_etf_data(self, ticker: str, start_date: datetime, end_date: datetime) -> List[PriceData]:
        # Convert ticker to lowercase for table lookup
        ticker_lower = ticker.lower()
        
        # ETF price schemas to search through
        etf_schemas = [
            "equity_etfs_prices",
            "cryptocurrency_etfs_prices", 
            "fixed_income_etfs_prices",
            "commodity_etfs_prices",
            "alternative_etfs_prices"
        ]
        
        conn = get_connection("etf_prices")
        if not conn:
            print("Could not connect to etf_prices database")
            return []
            
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Search through each ETF schema for the ticker table
                for schema_name in etf_schemas:
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = %s AND tablename = %s
                    """, (schema_name, ticker_lower))
                    
                    table_info = cursor.fetchone()
                    if table_info:
                        # Found the ticker table, now query the data
                        cursor.execute(f"""
                            SELECT datetime as date, open, high, low, close, volume
                            FROM {schema_name}.{ticker_lower}
                            WHERE datetime >= %s AND datetime <= %s
                            ORDER BY datetime
                        """, (start_date, end_date))
                        
                        rows = cursor.fetchall()
                        return [PriceData(**dict(row)) for row in rows]
                
                print(f"Ticker '{ticker}' not found in any ETF price schema")
                return []
            
        except psycopg2.Error as e:
            print(f"Error searching in etf_prices database: {e}")
            return []
        finally:
            conn.close()

