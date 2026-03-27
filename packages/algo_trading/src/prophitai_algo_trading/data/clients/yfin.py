import yfinance as yf
import pandas as pd
from zoneinfo import ZoneInfo

def get_yf_intraday_prices(symbol: str, interval: str = '1m', period: str = '1d'):
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True)

    if df.empty:
        return []
    
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    df.reset_index(inplace=True)
    df = df.rename(columns={'Datetime': 'date'})
    
    # Convert UTC to Eastern time and remove timezone
    df['date'] = df['date'].dt.tz_convert(ZoneInfo('America/New_York')).dt.tz_localize(None)
    
    # Return as list of dicts (newest first)
    return df.to_dict('records')[::-1]