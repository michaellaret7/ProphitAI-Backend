# Todo List - Code Duplication Removal in Simulated Shocks

## Completed Tasks
✅ Remove wildcard imports and make them explicit
✅ Extract duplicate price data fetching logic into a reusable function  
✅ Refactor simulated_market_shock to use helper functions
✅ Refactor multi_factor_market_shock to use helper functions

## Review
Successfully removed all code duplication from the simulated shocks folder:

1. **Fixed wildcard imports** - Replaced `import *` with explicit imports in run_report.py

2. **Created reusable helper functions**:
   - `fetch_price_data_for_tickers()` - Centralized parallel price data fetching  
   - `calculate_betas_for_portfolio()` - Centralized beta calculation logic

3. **Refactored existing functions** to use the new helpers, eliminating ~80 lines of duplicate code

4. **No linting errors** introduced

The code is now more maintainable, follows DRY principle, and is easier to understand.