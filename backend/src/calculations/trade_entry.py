import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

import requests


class PositionType(Enum):
    """Position type for trading"""
    LONG = "long"
    SHORT = "short"


@dataclass
class EntrySignal:
    """Entry signal data structure"""
    ticker: str
    position_type: PositionType
    entry_price: float
    current_price: float
    signal_strength: str  # 'strong', 'moderate', 'weak', 'neutral'
    indicators: Dict[str, any]  # Store indicator values
    

# Example usage and testing functions
def get_data_daily(ticker: str, days: int = 60) -> pd.DataFrame:
    """
    Get daily OHLCV data for the last N days using FMP API
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to retrieve (default 60)
    
    Returns:
        DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        Index is datetime
    """
    from backend.src.db.core.pull_fmp_data import FMP_API_DATA
    
    fmp_api = FMP_API_DATA()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get daily data from FMP API
    response = fmp_api.get_daily_prices_for_ticker(ticker, start_date, end_date)
    
    if not response or 'historical' not in response:
        raise ValueError(f"Failed to get data for {ticker} from FMP API")
    
    # Extract historical data
    historical_data = response['historical']
    
    # Convert to DataFrame
    df = pd.DataFrame(historical_data)
    
    # Rename columns to match expected format
    column_mapping = {
        'date': 'date',
        'open': 'open',
        'high': 'high', 
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    
    # Select and rename columns
    df = df[list(column_mapping.keys())].rename(columns=column_mapping)
    
    # Convert date to datetime and set as index
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    # Convert numeric columns
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def spot_price(ticker: str):
    from dotenv import load_dotenv
    import os

    load_dotenv()

    API_KEY = os.getenv("FMP_API_KEY")

    url = f'https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={API_KEY}'

    response = requests.get(url)
    data = response.json()

    return data[0]['price']

# Technical Indicator Functions
def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        df: DataFrame with 'close' prices
        period: RSI period (default 14 days)
    
    Returns:
        Series with RSI values
    """
    close_prices = df['close']
    
    # Calculate price changes
    delta = close_prices.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses
    avg_gains = gains.rolling(window=period, min_periods=1).mean()
    avg_losses = losses.rolling(window=period, min_periods=1).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_moving_averages(df: pd.DataFrame, short_period: int = 20, long_period: int = 50) -> Dict[str, pd.Series]:
    """
    Calculate Simple Moving Averages
    
    Args:
        df: DataFrame with 'close' prices
        short_period: Short-term MA period (default 20 days)
        long_period: Long-term MA period (default 50 days)
    
    Returns:
        Dictionary with 'sma_short' and 'sma_long' Series
    """
    return {
        'sma_short': df['close'].rolling(window=short_period, min_periods=1).mean(),
        'sma_long': df['close'].rolling(window=long_period, min_periods=1).mean()
    }


def find_support_resistance(df: pd.DataFrame, window: int = 20, min_touches: int = 2) -> Dict[str, List[float]]:
    """
    Find support and resistance levels based on price history
    
    Args:
        df: DataFrame with OHLC prices
        window: Rolling window for finding local min/max
        min_touches: Minimum number of touches to confirm level
    
    Returns:
        Dictionary with 'support' and 'resistance' levels
    """
    # Find local highs and lows
    highs = df['high'].rolling(window=window, center=True).max()
    lows = df['low'].rolling(window=window, center=True).min()
    
    # Identify peaks and troughs
    resistance_levels = []
    support_levels = []
    
    # Find resistance levels (local maxima)
    for i in range(window, len(df) - window):
        if df['high'].iloc[i] == highs.iloc[i]:
            level = df['high'].iloc[i]
            # Check if this level has multiple touches
            touches = ((df['high'] >= level * 0.98) & (df['high'] <= level * 1.02)).sum()
            if touches >= min_touches:
                resistance_levels.append(level)
    
    # Find support levels (local minima)
    for i in range(window, len(df) - window):
        if df['low'].iloc[i] == lows.iloc[i]:
            level = df['low'].iloc[i]
            # Check if this level has multiple touches
            touches = ((df['low'] >= level * 0.98) & (df['low'] <= level * 1.02)).sum()
            if touches >= min_touches:
                support_levels.append(level)
    
    # Remove duplicates and sort
    resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:3]  # Keep top 3
    support_levels = sorted(list(set(support_levels)))[:3]  # Keep bottom 3
    
    return {
        'support': support_levels,
        'resistance': resistance_levels
    }


def determine_entry_point(ticker: str, position_type: PositionType, days: int = 60, debug: bool = False) -> EntrySignal:
    """
    Determine optimal entry point for a position
    
    Args:
        ticker: Stock ticker symbol
        position_type: LONG or SHORT position
        days: Number of days of historical data to analyze
        debug: If True, print debug information about signals
    
    Returns:
        EntrySignal with recommended entry price and analysis
    """
    # Get price data
    df = get_data_daily(ticker, days)
    current_spot = spot_price(ticker)
    
    # Calculate indicators
    df['rsi'] = calculate_rsi(df)
    mas = calculate_moving_averages(df)
    df['sma_short'] = mas['sma_short']
    df['sma_long'] = mas['sma_long']
    levels = find_support_resistance(df)
    
    # Get latest indicator values
    latest_rsi = df['rsi'].iloc[-1]
    latest_sma_short = df['sma_short'].iloc[-1]
    latest_sma_long = df['sma_long'].iloc[-1]
    ma_trend = 'bullish' if latest_sma_short > latest_sma_long else 'bearish'
    
    # Initialize signal strength
    signal_strength = 'weak'
    entry_price = current_spot
    
    if debug:
        print(f"\nDebug Info for {ticker}:")
        print(f"  RSI: {latest_rsi:.2f}")
        print(f"  MA Trend: {ma_trend} (SMA20: ${latest_sma_short:.2f}, SMA50: ${latest_sma_long:.2f})")
        print(f"  Support Levels: {levels['support']}")
        print(f"  Resistance Levels: {levels['resistance']}")
        print(f"  Current Price: ${current_spot:.2f}")
    
    if position_type == PositionType.LONG:
        # Long position logic
        rsi_signal = latest_rsi < 40  # More practical oversold threshold
        ma_signal = ma_trend == 'bullish'
        
        # Check proximity to support
        near_support = False
        if levels['support']:
            nearest_support = min(levels['support'], key=lambda x: abs(x - current_spot))
            near_support = (current_spot <= nearest_support * 1.05)  # Within 5% of support
        
        # Determine signal strength
        if debug:
            print(f"  LONG Signals: RSI={rsi_signal}, MA={ma_signal}, Support={near_support}")
        
        signals_count = sum([rsi_signal, ma_signal, near_support])
        if signals_count >= 3:
            signal_strength = 'strong'
            entry_price = current_spot * 0.995  # Entry slightly below current price
        elif signals_count >= 2:
            signal_strength = 'moderate'
            entry_price = current_spot * 0.998
        elif signals_count >= 1:
            signal_strength = 'weak'
            entry_price = current_spot * 0.999  # Very slight adjustment for weak signal
        else:
            signal_strength = 'neutral'
            entry_price = current_spot  # No adjustment when no signals
            
    else:  # SHORT position
        # Short position logic
        rsi_signal = latest_rsi > 60  # More practical overbought threshold
        ma_signal = ma_trend == 'bearish'
        
        # Check proximity to resistance
        near_resistance = False
        if levels['resistance']:
            nearest_resistance = min(levels['resistance'], key=lambda x: abs(x - current_spot))
            near_resistance = (current_spot >= nearest_resistance * 0.95)  # Within 5% of resistance
        
        # Determine signal strength
        if debug:
            print(f"  SHORT Signals: RSI={rsi_signal}, MA={ma_signal}, Resistance={near_resistance}")
        
        signals_count = sum([rsi_signal, ma_signal, near_resistance])
        if signals_count >= 3:
            signal_strength = 'strong'
            entry_price = current_spot * 1.005  # Entry slightly above current price
        elif signals_count >= 2:
            signal_strength = 'moderate'
            entry_price = current_spot * 1.002
        elif signals_count >= 1:
            signal_strength = 'weak'
            entry_price = current_spot * 1.001  # Very slight adjustment for weak signal
        else:
            signal_strength = 'neutral'
            entry_price = current_spot  # No adjustment when no signals
    
    return EntrySignal(
        ticker=ticker,
        position_type=position_type,
        entry_price=round(entry_price, 2),
        current_price=round(current_spot, 2),
        signal_strength=signal_strength,
        indicators={
            'rsi': round(latest_rsi, 2),
            'ma_trend': ma_trend,
            'sma_short': round(latest_sma_short, 2),
            'sma_long': round(latest_sma_long, 2),
            'support_levels': levels['support'],
            'resistance_levels': levels['resistance']
        }
    )


def get_entry_prices(portfolio: Dict[str, Tuple[float, str]], debug: bool = False) -> List[EntrySignal]:
    """
    Get entry prices for a portfolio of positions
    
    Args:
        portfolio: Dictionary with ticker as key and (weight, position_type) as value
                  e.g., {'AAPL': (0.2, 'long'), 'TSLA': (0.1, 'short')}
        debug: If True, print debug information about signals
    
    Returns:
        List of EntrySignal objects for each position
    """
    entry_signals = []
    
    for ticker, (weight, pos_type) in portfolio.items():
        position_type = PositionType.LONG if pos_type.lower() == 'long' else PositionType.SHORT
        signal = determine_entry_point(ticker, position_type, debug=debug)
        entry_signals.append(signal)
        
        print(f"\n{ticker} ({pos_type.upper()}) - Weight: {weight*100:.1f}%")
        print(f"  Current Price: ${signal.current_price}")
        print(f"  Entry Price: ${signal.entry_price}")
        print(f"  Signal Strength: {signal.signal_strength}")
        print(f"  RSI: {signal.indicators['rsi']}")
        print(f"  MA Trend: {signal.indicators['ma_trend']}")
    
    return entry_signals


# Example usage
if __name__ == "__main__":
    # Example 1: Single stock entry point
    portfolio = {
        "WMT": (0.05, "long"),
        "PPC": (0.05, "short"),
        "INGR": (0.05, "long"),
    }

    entry_signals = get_entry_prices(portfolio, debug=False)
    for signal in entry_signals:
        print(signal.ticker)
        print(signal.entry_price)
