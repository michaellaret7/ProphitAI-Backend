# Fix Stress Test Runner Bottleneck

## Problem Statement
The runner.py file fetches price data for all 41 tickers multiple times (once per scenario). With 12 scenarios (6 historical, 6 hypothetical), this causes 12x redundant data fetching since betas don't change between scenarios.

## Solution Approach
Convert runner.py to a class-based structure that fetches data once during initialization and reuses it for all scenarios.

## Todo Items
- [x] 1. Create StressTestRunner class structure
- [x] 2. Move data fetching to initialization method
- [x] 3. Modify engine.py to accept pre-calculated betas
- [x] 4. Update runner to use cached betas for all scenarios
- [x] 5. Test the optimized implementation
- [x] 6. Clean up and document changes

## Expected Outcome
- Reduce data fetching from 12 times to 1 time
- Significant performance improvement (approx 12x faster)
- Cleaner, more maintainable code structure

## Review
### Changes Made:
1. **Created StressTestRunner class** - Converted runner.py from functions to a class-based structure
2. **Cached betas in initialization** - The class now fetches all price data and calculates betas once during `__init__`
3. **Modified engine.py** - Added optional `pre_calculated_betas` parameter to `run_stress_test_engine()`
4. **Optimized data flow** - Runner filters cached betas for each scenario instead of re-fetching
5. **Maintained backward compatibility** - Kept `run_stress_test_workflow()` function as a wrapper

### Performance Improvements:
- **Before**: 12 data fetches (one per scenario) × 41 tickers = 492 API calls
- **After**: 1 data fetch for all tickers and ETFs = ~50 API calls
- **Result**: ~10x reduction in API calls and significant speed improvement

### Code Quality:
- More modular and maintainable structure
- Clear separation of concerns (data fetching vs processing)
- No linting errors
- Backward compatible with existing code
