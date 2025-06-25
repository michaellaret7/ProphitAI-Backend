from typing import List
from datetime import datetime, timedelta
from backend.src.utils.database import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from decimal import Decimal
from backend.src.utils.caching import cache_result

class EquityPriceDataRepository:
    def __init__(self):
        pass
    
    @cache_result
    def fetch_equity_price_data(self, ticker: str, start_date: datetime, end_date: datetime, interval: str = '15T') -> pd.DataFrame:
        """
        Fetches equity price data and resamples it to the specified interval.

        Args:
            ticker (str): The stock ticker.
            start_date (datetime): The start of the date range.
            end_date (datetime): The end of the date range.
            interval (str): The desired time interval for the data. 
                            Accepts pandas frequency strings like '15T', '30T', '1H', '1D'.
                            Defaults to '15T'.

        Returns:
            pd.DataFrame: A DataFrame with the resampled price data, or an empty DataFrame if not found.
        """
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
                        
                        if not rows:
                            return pd.DataFrame()

                        data = []
                        for row in rows:
                            row_dict = dict(row)
                            # Convert Decimal values to float
                            for key, value in row_dict.items():
                                if isinstance(value, Decimal):
                                    row_dict[key] = float(value)
                            data.append(row_dict)
                        
                        df = pd.DataFrame(data)

                        if df.empty:
                            return pd.DataFrame()

                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        
                        if interval != '15T':
                            agg_dict = {
                                'open': 'first',
                                'high': 'max',
                                'low': 'min',
                                'close': 'last',
                                'volume': 'sum'
                            }
                            df = df.resample(interval).agg(agg_dict).dropna()

                        return df.reset_index()
                
            except psycopg2.Error as e:
                print(f"Error searching in {db_name}: {e}")
                continue
            finally:
                if conn:
                    conn.close()
        
        print(f"Ticker '{ticker}' not found in any database")
        return pd.DataFrame()
