# Entry Point Calculation Plan

## Objective
Create a simple, effective system to determine optimal entry prices for long and short stock positions using daily price data.

## Research Summary (from web search)
Based on research, the most effective methods for entry point calculation are:
1. **RSI (Relative Strength Index)**: Identifies overbought (>70) and oversold (<30) conditions
2. **Moving Average Crossovers**: Signals trend changes when short-term MA crosses long-term MA
3. **Support/Resistance Levels**: Historical price levels where reversals tend to occur
4. **Bollinger Bands**: Identifies price extremes based on volatility

## Implementation Plan

### Todo Items
- [x] Clear todo.md and create plan for entry point calculation
- [x] Research effective methods for calculating entry points (completed via web search)
- [x] Design entry point calculation system using RSI, Moving Averages, and Support/Resistance
- [x] Implement RSI calculation function for overbought/oversold signals
- [x] Implement Moving Average crossover detection for trend confirmation
- [x] Implement Support/Resistance level identification
- [x] Create main entry point determination function that combines indicators
- [x] Add example usage and testing code

## Technical Approach

### 1. RSI Calculation
- Calculate 14-day RSI from daily price data
- Long entry signal: RSI < 30 (oversold)
- Short entry signal: RSI > 70 (overbought)

### 2. Moving Averages
- Calculate 20-day SMA (short-term) and 50-day SMA (long-term)
- Long entry signal: 20-day crosses above 50-day
- Short entry signal: 20-day crosses below 50-day

### 3. Support/Resistance
- Identify price levels with multiple touches (at least 2-3)
- Long entry: Near support level
- Short entry: Near resistance level

### 4. Entry Price Determination
- Combine signals from all indicators
- For LONG positions:
  - Primary signal: RSI < 30 OR price near support
  - Confirmation: Moving average trend is bullish
  - Entry price: Current spot price or limit order slightly below
  
- For SHORT positions:
  - Primary signal: RSI > 70 OR price near resistance
  - Confirmation: Moving average trend is bearish
  - Entry price: Current spot price or limit order slightly above

## Code Structure
All code will be added to `backend/testing/trade_entry.py`:
1. `calculate_rsi()` - RSI calculation
2. `calculate_moving_averages()` - SMA calculations
3. `find_support_resistance()` - Identify key price levels
4. `determine_entry_point()` - Main function combining all indicators
5. `get_entry_prices()` - Wrapper function for portfolio positions

## Review - Implementation Complete

### Summary of Changes
Successfully implemented a complete entry point calculation system in `backend/testing/trade_entry.py` with the following components:

1. **Data Structures**:
   - `PositionType` enum for LONG/SHORT positions
   - `EntrySignal` dataclass to store entry point analysis results

2. **Technical Indicators Implemented**:
   - **RSI Calculation** (`calculate_rsi`): 14-day RSI to identify overbought/oversold conditions
   - **Moving Averages** (`calculate_moving_averages`): 20-day and 50-day SMAs for trend confirmation
   - **Support/Resistance** (`find_support_resistance`): Identifies key price levels from historical data

3. **Main Functions**:
   - **`determine_entry_point()`**: Core function that combines all indicators to determine optimal entry price
     - For LONG positions: Looks for oversold RSI (<30), bullish MA trend, and proximity to support
     - For SHORT positions: Looks for overbought RSI (>70), bearish MA trend, and proximity to resistance
     - Returns signal strength (strong/moderate/weak) based on number of confirming indicators
   - **`get_entry_prices()`**: Portfolio-level function that processes multiple positions at once

4. **Entry Price Logic**:
   - Strong signals (3 indicators agree): 0.5% adjustment from spot price
   - Moderate signals (2 indicators agree): 0.2% adjustment from spot price  
   - Weak signals (1 or fewer indicators): Use current spot price

5. **Example Usage**:
   - Single stock entry point analysis
   - Portfolio-wide entry point calculation with formatted output

### Key Features
- Simple, clean implementation following DRY principles
- Uses existing `get_data_daily()` and `spot_price()` functions as requested
- No stop loss, take profit, or risk/reward calculations - purely entry point focused
- Modular design with separate functions for each indicator
- Clear signal strength classification to help with decision making

### Usage
The system can be used in two ways:
1. **Single Position**: `determine_entry_point(ticker, PositionType.LONG/SHORT)`
2. **Portfolio**: `get_entry_prices({'AAPL': (0.2, 'long'), 'TSLA': (0.1, 'short'), ...})`

The implementation is complete and ready for testing with real portfolio data.

## Update - Improved Thresholds

### Issue Identified
The entry prices were showing the same as current prices with all "weak" signals because the original RSI thresholds (30/70) were too extreme and rarely occur in normal market conditions.

### Improvements Made
1. **Adjusted RSI Thresholds**:
   - LONG positions: RSI < 40 (was 30)
   - SHORT positions: RSI > 60 (was 70)
   
2. **Widened Support/Resistance Proximity**:
   - Now checks within 5% of levels (was 2%)
   
3. **Added Signal Gradation**:
   - 'strong': 3 indicators agree (0.5% price adjustment)
   - 'moderate': 2 indicators agree (0.2% price adjustment)
   - 'weak': 1 indicator agrees (0.1% price adjustment)
   - 'neutral': No indicators triggered (no adjustment)
   
4. **Added Debug Mode**:
   - Set `debug=True` in functions to see RSI values, MA trends, and which signals are triggering
   - Helps diagnose why certain entry points are recommended

### Usage with Debug
```python
# Single stock with debug info
signal = determine_entry_point("AAPL", PositionType.LONG, debug=True)

# Portfolio with debug info
portfolio_signals = get_entry_prices(portfolio, debug=True)
```

These adjustments make the system more practical for real-world trading conditions where extreme RSI values are rare.
