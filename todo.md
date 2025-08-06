# Stress Test Cleanup - Unused Functions and Imports

## Overview
Remove unused functions and imports from the simulated_shocks folder to improve code cleanliness and maintainability.

## Todo Items

### 1. Remove unused functions ✓
- Removed `simulated_market_shock()` function from engine.py ✓
- Removed `get_industry_distribution()` method from runner.py ✓

### 2. Remove unused imports ✓
- Removed `simulated_market_shock` import from runner.py ✓
- Removed `json` import from runner.py ✓
- Removed `MarketSession` import from runner.py ✓
- Removed `Ticker` import from runner.py ✓
- Removed `calculate_beta` import from engine.py ✓
- Removed `get_price_data_daily` import from engine.py ✓

### 3. Fix references ✓
- Fixed json.dumps reference in test code to use get_token_count ✓

## Review

### Summary of Changes
Successfully removed all unused functions and imports from the simulated_shocks folder:

1. **engine.py**: 
   - Removed the unused `simulated_market_shock()` function (75 lines)
   - Removed unused imports: `calculate_beta` and `get_price_data_daily`

2. **runner.py**: 
   - Removed the unused `get_industry_distribution()` method (10 lines)
   - Removed unused imports: `simulated_market_shock`, `json`, `MarketSession`, and `Ticker`
   - Fixed the test code to use `get_token_count()` instead of `json.dumps()`

### Benefits
- Cleaner, more maintainable codebase
- Reduced code size and complexity
- No unused imports or functions
- All functionality remains intact