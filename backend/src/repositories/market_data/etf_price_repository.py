from typing import List
from datetime import datetime
from backend.src.utils.database import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from decimal import Decimal

class ETFPriceDataRepository:
    def __init__(self):
        pass

    def fetch_etf_price_data(self, ticker: str, start_date: datetime, end_date: datetime, interval: str = '15T') -> pd.DataFrame:
        """
        Fetches ETF price data and resamples it to the specified interval.

        Args:
            ticker (str): The ETF ticker.
            start_date (datetime): The start of the date range.
            end_date (datetime): The end of the date range.
            interval (str): The desired time interval for the data. 
                            Accepts pandas frequency strings like '15T', '30T', '1H', '1D'.
                            Defaults to '15T'.

        Returns:
            pd.DataFrame: A DataFrame with the resampled price data, or an empty DataFrame if not found.
        """
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
            return pd.DataFrame()
            
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
                        
                        if not rows:
                            return pd.DataFrame()

                        # Convert to DataFrame directly with Decimal to float conversion
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
                
                print(f"Ticker '{ticker}' not found in any ETF price schema")
                return pd.DataFrame()
            
        except psycopg2.Error as e:
            print(f"Error searching in etf_prices database: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

