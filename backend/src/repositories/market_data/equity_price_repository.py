from typing import List
from datetime import datetime
from backend.src.data_models.market_data_models import PriceData
from backend.src.utils.database import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

class EquityPriceDataRepository:
    def __init__(self):
        pass
    
    def fetch_equity_price_data(self, ticker: str, start_date: datetime, end_date: datetime) -> List[PriceData]:
        # Try different database connections to find the ticker
        possible_databases = [
            "equity_sector_communication_services_prices",
            "equity_sector_consumer_discretionary_prices",
            "equity_sector_consumer_staples_prices",
            "equity_sector_energy_prices",
            "equity_sector_financials_prices",
            "equity_sector_health_care_prices",
            "equity_sector_industrials_prices",
            "equity_sector_information_technology_prices",
            "equity_sector_materials_prices",
            "equity_sector_real_estate_prices",
            "equity_sector_utilities_prices"
        ]

        ticker = ticker.lower()
        
        for db_name in possible_databases:
            conn = get_connection(db_name)
            if not conn:
                continue
                
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # First, find which schema contains the ticker table
                    cursor.execute("""
                        SELECT schemaname, tablename 
                        FROM pg_tables 
                        WHERE tablename = %s
                    """, (ticker,))
                    
                    table_info = cursor.fetchone()
                    if table_info:
                        schema_name = table_info['schemaname']
                        
                        # Now query the actual data
                        cursor.execute(f"""
                            SELECT date, open, high, low, close, volume
                            FROM {schema_name}.{ticker}
                            WHERE date >= %s AND date <= %s
                            ORDER BY date
                        """, (start_date, end_date))
                        
                        rows = cursor.fetchall()
                        conn.close()
                        return [PriceData(**dict(row)) for row in rows]
                
            except psycopg2.Error as e:
                print(f"Error searching in {db_name}: {e}")
                continue
            finally:
                conn.close()
        
        print(f"Ticker '{ticker}' not found in any database")
        return []

