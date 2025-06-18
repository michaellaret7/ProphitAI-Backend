import time
import traceback
from datetime import datetime, timedelta
import pandas as pd
from ib_insync import IB, Stock, util
from src.utils.ib_utils import connect_to_ib, disconnect_from_ib

# IBKR FULL HIST DATA
def get_5y_data(ib, symbol):
    try:
        contract = Stock(symbol, 'SMART', 'USD')
        
        # Helper function to safely convert to DataFrame and check if empty
        def safe_convert_and_check(bars_data):
            if bars_data is None:
                return None
            
            # If it's already a DataFrame, just check if it's empty
            if isinstance(bars_data, pd.DataFrame):
                return None if bars_data.empty else bars_data
                
            # If it's a BarDataList from IB, convert to DataFrame
            try:
                df = util.df(bars_data)
                return None if df.empty else df
            except Exception as e:
                print(f"Error converting data: {e}")
                return None
            
        # Rest of your get_date function remains the same
        def get_date(df):
            if df is None or df.empty:
                return None
            
            if 'date' in df.columns:
                first_date_str = df['date'].iloc[0]
                first_date = pd.to_datetime(first_date_str)
                print(f"First date in data: {first_date}")

                # Calculate the day before
                previous_date = first_date.date() - timedelta(days=1)
                previous_date = str(previous_date).replace('-', '')
                print(f"Date from the day before: {previous_date}")
                return previous_date
            else:
                print("No date column found.")
                return None

        # YEAR 1
        try:
            bars_raw = ib.reqHistoricalData(
                contract, 
                endDateTime='',
                durationStr='1 Y', 
                barSizeSetting='15 mins', 
                whatToShow='TRADES', 
                useRTH=False,
                formatDate=1
            )
            
            # Safely convert to DataFrame
            bars = safe_convert_and_check(bars_raw)
            if bars is None:
                print(f"⚠️ No valid data for {symbol} in first year")
                return None
                
            # Add datetime column and filter
            bars['datetime'] = pd.to_datetime(bars['date'])
            # Keep only data between 9:30 AM and 4:00 PM ET
            bars = bars[
                (bars['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                (bars['datetime'].dt.time <= pd.to_datetime('16:00').time())
            ]
            
            if bars.empty:
                print(f"⚠️ No valid trading hours data for {symbol}")
                return None
                
            previous_date = get_date(bars)
            if not previous_date:
                print(f"⚠️ Could not determine previous date for {symbol}")
                return bars  # Return what we have so far
                
        except Exception as e:
            print(f"⚠️ Error fetching first year data for {symbol}: {e}")
            return None

        time.sleep(1)

        # Initialize DataFrames for additional years
        bars2, bars3, bars4, bars5 = None, None, None, None
        
        # YEAR 2
        try:
            bars2_raw = ib.reqHistoricalData(
                contract, 
                endDateTime=previous_date + ' 18:00:00',
                durationStr='1 Y', 
                barSizeSetting='15 mins', 
                whatToShow='TRADES', 
                useRTH=False,
                formatDate=1
            )
            
            # Safely convert to DataFrame
            bars2 = safe_convert_and_check(bars2_raw)
            if bars2 is None:
                print(f"No data returned for {symbol} in second year - continuing with first year data only")
            else:
                bars2['datetime'] = pd.to_datetime(bars2['date'])
                # Filter trading hours
                bars2 = bars2[
                    (bars2['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                    (bars2['datetime'].dt.time <= pd.to_datetime('16:00').time())
                ]
                
                if bars2.empty:
                    bars2 = None
                    print(f"No valid trading hours data for {symbol} in second year")
                    previous_date2 = None
                else:
                    previous_date2 = get_date(bars2)
            
        except Exception as e:
            print(f"Error fetching second year data for {symbol}: {e} - continuing with available data")
            previous_date2 = None
            bars2 = None

        time.sleep(1)

        # YEAR 3 - Only proceed if we have previous_date2
        if previous_date2:
            try:
                bars3_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date2 + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                bars3 = safe_convert_and_check(bars3_raw)
                if bars3 is None:
                    print(f"No data returned for {symbol} in third year - continuing with available data")
                    previous_date3 = None
                else:
                    bars3['datetime'] = pd.to_datetime(bars3['date'])
                    bars3 = bars3[
                        (bars3['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars3['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars3.empty:
                        bars3 = None
                        print(f"No valid trading hours data for {symbol} in third year")
                        previous_date3 = None
                    else:
                        previous_date3 = get_date(bars3)
                
            except Exception as e:
                print(f"Error fetching third year data for {symbol}: {e} - continuing with available data")
                previous_date3 = None
                bars3 = None
        else:
            previous_date3 = None
            bars3 = None

        time.sleep(1)

        # YEAR 4 - Only proceed if we have previous_date3
        if previous_date3:
            try:
                bars4_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date3 + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                bars4 = safe_convert_and_check(bars4_raw)
                if bars4 is None:
                    print(f"No data returned for {symbol} in fourth year - continuing with available data")
                    previous_date4 = None
                else:
                    bars4['datetime'] = pd.to_datetime(bars4['date'])
                    bars4 = bars4[
                        (bars4['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars4['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars4.empty:
                        bars4 = None
                        print(f"No valid trading hours data for {symbol} in fourth year")
                        previous_date4 = None
                    else:
                        previous_date4 = get_date(bars4)
                
            except Exception as e:
                print(f"Error fetching fourth year data for {symbol}: {e} - continuing with available data")
                previous_date4 = None
                bars4 = None
        else:
            previous_date4 = None
            bars4 = None

        time.sleep(1)

        # YEAR 5 - Only proceed if we have previous_date4
        if previous_date4:
            try:
                bars5_raw = ib.reqHistoricalData(
                    contract, 
                    endDateTime=previous_date4 + ' 18:00:00',
                    durationStr='1 Y', 
                    barSizeSetting='15 mins', 
                    whatToShow='TRADES', 
                    useRTH=False,
                    formatDate=1
                )
                
                bars5 = safe_convert_and_check(bars5_raw)
                if bars5 is None:
                    print(f"No data returned for {symbol} in fifth year - continuing with available data")
                else:
                    bars5['datetime'] = pd.to_datetime(bars5['date'])
                    bars5 = bars5[
                        (bars5['datetime'].dt.time >= pd.to_datetime('09:30').time()) & 
                        (bars5['datetime'].dt.time <= pd.to_datetime('16:00').time())
                    ]
                    
                    if bars5.empty:
                        bars5 = None
                        print(f"No valid trading hours data for {symbol} in fifth year")
                
            except Exception as e:
                print(f"Error fetching fifth year data for {symbol}: {e} - continuing with available data")
                bars5 = None
        else:
            bars5 = None

        # Prepare list of DataFrames to concatenate
        # This is where the error was occurring - now we've already ensured all are DataFrames
        dfs_to_concat = []
        for i, df in enumerate([bars, bars2, bars3, bars4, bars5], 1):
            if df is not None and not df.empty:
                dfs_to_concat.append(df)
                print(f"✅ Year {i} data will be included: {len(df)} rows")
            else:
                print(f"❌ Year {i} data not available")
        
        if not dfs_to_concat:
            print(f"⚠️ No valid data frames to concatenate for {symbol}")
            return None
        
        # Concatenate the DataFrames and sort by datetime
        print(f"🔄 Combining data from {len(dfs_to_concat)} years...")
        combined_bars = pd.concat(dfs_to_concat, ignore_index=True)
        combined_bars = combined_bars.sort_values('datetime').reset_index(drop=True)
        # Remove any duplicate rows based on datetime
        combined_bars = combined_bars.drop_duplicates(subset='datetime', keep='first')
        print(f"📊 Combined and deduplicated bars for {symbol}: {len(combined_bars)} records")
        
        if len(combined_bars) > 0:
            print(combined_bars.head())
            if len(combined_bars) > 5:
                print("...")
                print(combined_bars.tail())
        else:
            print("No data available.")
        
        return combined_bars
        
    except Exception as e:
        print(f"⚠️ Unexpected error in get_5y_data for {symbol}: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    ib = connect_to_ib()
    if ib:
        try:
            ticker = 'AAPL'
            data = get_5y_data(ib, ticker)
            
            if data is not None and not data.empty:
                print(f"\n✅ Retrieved {len(data)} rows of data for {ticker}")
                print("\nFirst few rows:")
                print(data.head())
                print("\nLast few rows:")
                print(data.tail())
            else:
                print(f"⚠️ No data available for {ticker}")

        finally:
            disconnect_from_ib()
            print("Disconnected from IB") 