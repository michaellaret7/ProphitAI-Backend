"""
Data retrieval utilities for fetching price and fundamental data from the database.
"""
import os
import pandas as pd
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Union
from backend.src.utils.database import get_default_db_config, get_db_connection
from backend.src.utils.file_utils import load_schema_data
from backend.src.utils.caching import cache_result


@cache_result
def get_price_data(ticker: str, frequency: str = 'daily', years: float = 4, 
                   db_config: Optional[Dict] = None,
                   start_date_override: Optional[str] = None,
                   end_date_override: Optional[str] = None) -> Optional[Union[pd.DataFrame, Dict]]:
    """
    Retrieve price data for a given ticker with specified frequency.
    
    Args:
        ticker: Stock ticker symbol
        frequency: 'daily' for daily closing prices or 'hourly' for hourly data
        years: Number of years of historical data to retrieve (used if overrides are not provided)
        db_config: Database configuration (uses default if None)
        start_date_override: Optional 'YYYY-MM-DD' string to specify exact start date
        end_date_override: Optional 'YYYY-MM-DD' string to specify exact end date
        
    Returns:
        For 'daily': DataFrame with columns [date, close, volume]
        For 'hourly': Dict with format {ticker: [data]}
        None if ticker not found or error
    """
    # Database configuration
    if db_config is None:
        db_config = get_default_db_config()
    
    # Normalize ticker
    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()
    
    # Calculate date range
    if start_date_override and end_date_override:
        try:
            start_date = datetime.strptime(start_date_override, '%Y-%m-%d')
            # For end_date, set time to end of day to include all records on that day
            end_date = datetime.strptime(end_date_override, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            print("Invalid date format for overrides. Please use 'YYYY-MM-DD'.")
            return None
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
    
    # Load schema definition
    schema_data = load_schema_data()
    
    # Find ticker location
    ticker_location = None
    for sector_name, sector_info in schema_data.items():
        database = sector_info.get('database')
        schemas = sector_info.get('schemas', {})
        
        for schema_name, schema_info in schemas.items():
            tables = schema_info.get('tables', {})
            
            for table_name, table_info in tables.items():
                tickers = table_info.get('tickers', [])
                
                # Case-insensitive comparison
                for db_ticker in tickers:
                    if ticker_upper.upper() == db_ticker.upper():
                        # Special case for ETFs - use specific database names
                        if "etf" in sector_name.lower():
                            db_name = "etf_prices"
                        else:
                            db_name = f"{database}_prices"
                            
                        ticker_location = {
                            "database": db_name,
                            "schema": f"{schema_name}_prices",
                            "ticker": db_ticker  # Use the ticker with the exact case from the database
                        }
                        break
            if ticker_location: break
        if ticker_location: break
    
    if not ticker_location:
        return None
    
    try:
        # Connect to database using context manager
        with get_db_connection(ticker_location['database'], db_config) as conn:
            cursor = conn.cursor()
            
            if frequency == 'daily':
                # Query only the last bar of each day for close price, and sum daily volume
                query = f"""
                WITH ranked_data AS (
                    SELECT 
                        datetime,
                        CAST(date AS DATE) as trading_date,
                        close,
                        volume,
                        ROW_NUMBER() OVER(PARTITION BY CAST(date AS DATE) ORDER BY datetime DESC) as rn,
                        SUM(volume) OVER(PARTITION BY CAST(date AS DATE)) as daily_total_volume
                    FROM {ticker_location['schema']}.{ticker_lower}
                    WHERE date >= %s
                )
                SELECT 
                   trading_date as date,
                   close,
                   daily_total_volume as volume
                FROM ranked_data
                WHERE rn = 1
                ORDER BY trading_date ASC
                """
                
                cursor.execute(query, (start_date.strftime('%Y-%m-%d'),))
                
                # Convert results
                results = []
                for row in cursor.fetchall():
                    date_val, close_val, volume_val = row
                    
                    if isinstance(close_val, Decimal):
                        close_val = float(close_val)
                        
                    # Ensure volume is an integer
                    if volume_val is None:
                        volume_val = 0
                    elif isinstance(volume_val, (Decimal, float)):
                        volume_val = int(volume_val)
                        
                    results.append({
                        "date": date_val.strftime('%Y-%m-%d'),
                        "close": close_val,
                        "volume": volume_val
                    })

                df = pd.DataFrame(results)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                return df
                
            elif frequency == 'hourly':
                # Query hourly data (taking the last 15-min bar of each hour)
                query = f"""
                WITH hourly_data AS (
                    SELECT 
                        date_trunc('hour', datetime) as hour_start,
                        MAX(datetime) as last_bar_time
                    FROM {ticker_location['schema']}.{ticker_lower}
                    WHERE datetime BETWEEN %s AND %s
                    GROUP BY date_trunc('hour', datetime)
                )
                SELECT 
                    hd.hour_start as datetime,
                    t.open,
                    t.high,
                    t.low,
                    t.close,
                    t.volume
                FROM hourly_data hd
                JOIN {ticker_location['schema']}.{ticker_lower} t
                    ON t.datetime = hd.last_bar_time
                ORDER BY hd.hour_start
                """
                
                cursor.execute(query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                
                # Convert results
                results = []
                for row in cursor.fetchall():
                    datetime_val, open_val, high_val, low_val, close_val, volume_val = row
                    
                    # Convert Decimal types to float
                    if isinstance(open_val, Decimal):
                        open_val = float(open_val)
                    if isinstance(high_val, Decimal):
                        high_val = float(high_val)
                    if isinstance(low_val, Decimal):
                        low_val = float(low_val)
                    if isinstance(close_val, Decimal):
                        close_val = float(close_val)
                    if isinstance(volume_val, Decimal):
                        volume_val = float(volume_val)
                           
                    results.append({
                        "datetime": datetime_val,
                        "open": open_val,
                        "high": high_val,
                        "low": low_val,
                        "close": close_val,
                        "volume": volume_val
                    })

                # Create DataFrame and sort by datetime
                df = pd.DataFrame(results)
                if not df.empty:
                    df = df.sort_values('datetime')
                    
                    # Convert to dictionary in the requested format
                    data_dict = df.to_dict('records')
                    return {ticker_upper: data_dict}
                else:
                    return {ticker_upper: []}
            else:
                raise ValueError(f"Invalid frequency: {frequency}. Must be 'daily' or 'hourly'")
                
    except Exception as e:
        print(f"Error retrieving {frequency} data for {ticker}: {e}")
        return None


@cache_result
def get_fundamental_data(ticker: str, db_config: Optional[Dict] = None) -> Optional[Dict]:
    """
    Retrieve all fundamental data for a given stock across different tables
    (balance sheets, cash flow statements, financial metrics, etc.)
    
    Args:
        ticker: Stock ticker symbol
        db_config: Database configuration (uses default if None)
        
    Returns:
        Dict with keys for each statement type (e.g., 'balance_sheets', 'income_statements')
        None if ticker not found or error
    """
    # Database configuration
    if db_config is None:
        db_config = get_default_db_config()
    
    # Normalize ticker
    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()
    
    # Load schema definition
    schema_data = load_schema_data()
    
    # Find ticker location
    ticker_location = None
    for sector_name, sector_info in schema_data.items():
        database = sector_info.get('database')
        schemas = sector_info.get('schemas', {})
        
        for schema_name, schema_info in schemas.items():
            tables = schema_info.get('tables', {})
            
            for table_name, table_info in tables.items():
                tickers = table_info.get('tickers', [])
                
                # Case-insensitive comparison
                for db_ticker in tickers:
                    if ticker_upper.upper() == db_ticker.upper():
                        # Special case for ETFs - use specific database names
                        if "etf" in sector_name.lower():
                            db_name = database
                        else:
                            db_name = f"{database}_fundamentals"
                            
                        ticker_location = {
                            "database": db_name,
                            "schema": f"{schema_name}",
                            "ticker": db_ticker
                        }
                        break
            if ticker_location: break
        if ticker_location: break
    
    # If the ticker is identified as an ETF, return empty data immediately
    if ticker_location and ticker_location.get('database') == 'etf_data':
        print(f"Ticker {ticker_upper} identified as ETF, skipping fundamental data retrieval.")
        return {}
    
    if not ticker_location:
        print(f"Ticker {ticker_upper} not found in any database schema for fundamentals.")
        return None
    
    try:
        # Connect to database using context manager
        with get_db_connection(ticker_location['database'], db_config) as conn:
            cursor = conn.cursor()
            
            # Define fundamental table types
            table_types = [
                "balance_sheets",
                "cash_flow_statements", 
                "financial_metrics",
                "income_statements"
            ]
            
            # Dictionary to store all fundamental data
            fundamental_data = {}
            
            # Large number columns that should have comma formatting
            large_number_columns = [
                'market_cap', 'revenue', 'total_assets', 'total_liabilities', 
                'total_equity', 'total_debt', 'net_income', 'operating_income',
                'gross_profit', 'ebitda', 'cash_flow', 'capex', 'fcf', 'dividends_paid',
                'shares_outstanding', 'total_cash', 'current_assets', 'current_liabilities'
            ]
            
            # Query each table type
            for table_type in table_types:
                table_name = f"{ticker_lower}_{table_type}"
                
                try:
                    # Check if table exists
                    check_query = f"""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables 
                       WHERE table_schema = '{ticker_location['schema']}'
                       AND table_name = '{table_name}'
                    )
                    """
                    cursor.execute(check_query)
                    table_exists = cursor.fetchone()[0]
                    
                    if not table_exists:
                        print(f"Table {table_name} does not exist, skipping")
                        continue
                    
                    # First check if data exists from 2015
                    check_data_query = f"""
                    SELECT COUNT(*) 
                    FROM {ticker_location['schema']}.{table_name}
                    WHERE date >= '2015-01-01'
                    """
                    cursor.execute(check_data_query)
                    data_count = cursor.fetchone()[0]
                    
                    # Query table data - from 2015 if data exists, otherwise all data
                    if data_count > 0:
                        query = f"""
                        SELECT *
                        FROM {ticker_location['schema']}.{table_name}
                        WHERE date >= '2015-01-01'
                        ORDER BY date
                        """
                    else:
                        # Fallback to all data if no data from 2015
                        query = f"""
                        SELECT *
                        FROM {ticker_location['schema']}.{table_name}
                        ORDER BY date
                        """
                    
                    cursor.execute(query)
                    
                    # Get column names
                    column_names = [desc[0] for desc in cursor.description]
                    
                    # Convert results
                    results = []
                    for row in cursor.fetchall():
                        # Convert row to dict
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = column_names[i]
                            # Convert Decimal to float
                            if isinstance(value, (Decimal, float)):
                                value = float(value)
                            row_dict[col_name] = value
                                
                        results.append(row_dict)
                    
                    # Create DataFrame and handle data types
                    df = pd.DataFrame(results)
                    
                    # Process dates
                    if 'date' in df.columns and not df.empty:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date')
                    
                    # Process numeric columns
                    for col in df.columns:
                        # Skip date and non-numeric columns
                        if col in ['date', 'ticker', 'currency', 'period', 'report_period', 'calendar_date']:
                            continue
                            
                        # Convert to numeric and round
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            df[col] = df[col].round(2)
                        except:
                            pass
                    
                    # Convert DataFrame to formatted dictionary
                    formatted_data = []
                    for _, row in df.iterrows():
                        formatted_row = {}
                        for col, val in row.items():
                            # Format date columns to ISO format
                            if col == 'date' and pd.notna(val):
                                formatted_row[col] = val.strftime('%Y-%m-%d')
                            # Keep numeric values as actual numbers for better LLM analysis
                            elif pd.api.types.is_numeric_dtype(type(val)) and pd.notna(val):
                                formatted_row[col] = float(val) if col.lower() not in large_number_columns else int(val)
                            # Handle any other values including NaN/None
                            else:
                                formatted_row[col] = str(val) if pd.notna(val) else None
                        
                        formatted_data.append(formatted_row)
                    
                    # Add to the fundamental data dictionary
                    fundamental_data[table_type] = formatted_data
                    
                except Exception as e:
                    print(f"Error retrieving {table_type} data: {e}")
                    fundamental_data[table_type] = []
            
            return fundamental_data
        
    except Exception as e:
        print(f"Error retrieving fundamental data for {ticker}: {e}")
        return None 


if __name__ == "__main__":
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 12, 31)
    
    qqq_data = get_price_data(
        ticker='QQQ',
        frequency='daily',
        start_date_override=start_date.strftime('%Y-%m-%d'),
        end_date_override=end_date.strftime('%Y-%m-%d')
    )
    
    iwm_data = get_price_data(
        ticker='IWM',
        frequency='daily',
        start_date_override=start_date.strftime('%Y-%m-%d'),
        end_date_override=end_date.strftime('%Y-%m-%d')
    )

    spy_data = get_price_data(
        ticker='SPY',
        frequency='daily',
        start_date_override=start_date.strftime('%Y-%m-%d'),
        end_date_override=end_date.strftime('%Y-%m-%d')
    )

    print(qqq_data)
    print(iwm_data)
    print(spy_data)
