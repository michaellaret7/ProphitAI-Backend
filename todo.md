# Fix Pairwise Correlation Analysis - Historical Only

## Problem Statement
The pairwise correlation analysis should only be run for historical scenarios, not hypothetical scenarios. It was also causing redundancy by being computed during initialization even when not needed.

## Solution Approach
1. Remove pairwise correlation from hypothetical scenarios
2. Implement lazy loading - compute only when first needed for historical scenarios
3. Optimize to avoid any unnecessary computations

## Todo Items
- [x] 1. Update pairwise correlation to only run for historical scenarios
- [x] 2. Move pairwise correlation out of class initialization
- [x] 3. Run pairwise correlation only when processing historical scenarios  
- [x] 4. Update documentation

## Review

### Changes Made:

1. **Removed from hypothetical scenarios**
   - Pairwise correlation is no longer included in hypothetical scenario results
   - Only historical scenarios include the correlation analysis

2. **Implemented lazy loading**
   - Pairwise correlation is no longer computed during class initialization
   - Added `_get_pairwise_correlation_analysis()` method that computes it on first access
   - Cached after first computation to avoid redundant calculations

3. **Optimized workflow**
   - If only hypothetical scenarios are run, pairwise correlation is never computed
   - Correlation analysis is computed once and reused for all historical scenarios

### Performance Improvements:

**Before:**
- Pairwise correlation computed on every initialization
- Included unnecessarily in hypothetical scenarios

**After:**
- Only computed when processing historical scenarios
- Computed once and cached
- Zero overhead for hypothetical-only workflows

### Code Quality:
- ✅ Cleaner separation of concerns
- ✅ Lazy loading pattern for better efficiency
- ✅ No linting errors
- ✅ Simple and maintainable
- ✅ Clear documentation of behavior