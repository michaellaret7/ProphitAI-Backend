# Stress Test Runner Bottleneck Fix

## Objective
Refactor runner.py into a class to fix data fetching bottleneck. Currently fetching price data and industry data multiple times (once per scenario).

## Todo Items

### 1. Analyze Current Bottlenecks
- [x] Identify repeated price data fetching in engine.py (line 79-86 in get_portfolio_betas)
- [x] Identify repeated industry data fetching in analysis.py (line 27-29 in industry_returns_analysis)
- [x] Document the data flow and redundancies (12 scenarios x 41+ tickers = 492+ fetches)

### 2. Design StressTestRunner Class
- [ ] Create class with initialization to fetch data once
- [ ] Store price data for all tickers and ETFs
- [ ] Store industry mapping for all tickers
- [ ] Pass pre-fetched data to engine and analysis functions

### 3. Refactor engine.py
- [ ] Modify get_portfolio_betas to accept pre-fetched price data
- [ ] Update function signatures to use cached data

### 4. Refactor analysis.py
- [ ] Modify industry_returns_analysis to accept industry mapping
- [ ] Remove database queries from analysis functions

### 5. Refactor runner.py
- [ ] Convert to StressTestRunner class
- [ ] Implement data caching in __init__
- [ ] Update workflow methods to use cached data

### 6. Test and Validate
- [ ] Ensure results remain identical
- [ ] Verify performance improvement
- [ ] Check all scenarios work correctly

## Notes
- Main bottleneck: Fetching ~41 ticker prices for each scenario (6 historical + 6 hypothetical = 12x fetches)
- Secondary bottleneck: Database queries for industry data in each scenario
- Solution: Fetch all data once in class initialization, reuse for all scenarios