# Calculations Folder Refactoring Plan - V2 Implementation

## Executive Summary
The calculations folder has grown organically over time and now suffers from inconsistency, code duplication, and poor maintainability. This plan outlines a comprehensive refactoring to create a modular, DRY-compliant, and maintainable calculation framework in the new `calculations_vtwo/` directory, allowing safe migration without disrupting existing functionality.

## Critical Issues Identified

### 1. Data Retrieval Chaos
**Current State:**
- **5 different data retrieval methods** across files:
  - Direct SQLAlchemy queries (growth, quality, value factors)
  - `get_price_data_daily()` (momentum, performance, returns)
  - `get_price_data_15_mins()` (portfolio returns)
  - `fetch_bulk_price_data_for_tickers()` (performance, risk)
  - `get_most_recent_price()` (value factors)
- No consistent data format or validation
- Session management scattered across files

### 2. Massive Code Duplication
**Duplicated Implementations:**
- **Sharpe Ratio**: 3 separate implementations
- **Annualized Returns**: 5 different implementations
- **Beta Calculation**: 4 implementations
- **Volatility**: 4 implementations
- **VaR**: 3 implementations
- **Returns Calculations**: Multiple inconsistent methods

### 3. Inconsistent Architecture
- Mix of classes, static methods, and standalone functions
- No clear inheritance or composition patterns
- Some files 1000+ lines (portfolio_returns_calculations.py: 464 lines)
- Empty placeholder files (sector_calculations)

### 4. Poor Error Handling & Validation
- Inconsistent None/NaN handling
- No standardized logging
- Missing input validation
- Silent failures in some cases

## Proposed Architecture

### Layer 1: Data Access Layer
```
calculations_vtwo/
├── data/
│   ├── __init__.py
│   ├── data_provider.py         # Unified data access interface
│   ├── price_fetcher.py         # Price data retrieval
│   └── fundamental_fetcher.py   # Fundamental data retrieval
```

### Layer 2: Core Calculations
```
├── core/
│   ├── __init__.py
│   ├── base_calculator.py       # Abstract base class
│   ├── returns.py               # All returns calculations
│   ├── volatility.py            # All volatility calculations
│   ├── risk_metrics.py          # VaR, CVaR, drawdown, etc.
│   ├── performance_metrics.py   # Sharpe, Sortino, Calmar, etc.
│   └── constants.py             # TRADING_DAYS, RISK_FREE_RATE, etc.
```

### Layer 3: Domain Calculators
```
├── factors/
│   ├── __init__.py
│   ├── base_factor.py          # Abstract factor class
│   ├── growth.py
│   ├── momentum.py
│   ├── quality.py
│   ├── value.py
│   └── volatility.py
│
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── portfolio_optimizer.py
│   ├── portfolio_analytics.py
│   └── position_sizing.py
```

## Implementation Steps

### Phase 1: Create Unified Data Layer (Week 1)
1. **Create DataProvider class**
   ```python
   class DataProvider:
       def get_price_data(ticker, start, end, frequency='daily')
       def get_fundamental_data(ticker, metrics)
       def get_bulk_data(tickers, start, end)
   ```
2. **Standardize data format**: Always return pd.DataFrame with consistent column names

### Phase 2: Extract Core Calculations (Week 1-2)
1. **Create base calculator class**
   ```python
   class BaseCalculator:
       def __init__(self, data_provider):
           self.data_provider = data_provider
       def validate_data(self, data)
       def handle_missing_data(self, data)
   ```

2. **Consolidate duplicate calculations**:
   - Move all Sharpe ratio calculations to `performance_metrics.py`
   - Move all volatility calculations to `volatility.py`
   - Move all returns calculations to `returns.py`
   - Move all VaR calculations to `risk_metrics.py`

### Phase 3: Refactor Factor Calculations (Week 2)
1. **Create BaseFactor class**:
   ```python
   class BaseFactor(BaseCalculator):
       def __init__(self, ticker, data_provider):
           self.ticker = ticker
           self.data = self._fetch_required_data()
       def calculate(self) -> FactorMetrics
   ```

2. **Refactor each factor to inherit from BaseFactor**
3. **Remove direct database queries** - use DataProvider instead

### Phase 4: Refactor Portfolio Calculations (Week 3)
1. **Break down large files**:
   - Split `correlation_portfolio_builder.py` (354 lines) into smaller modules
   - Extract visualization code to separate module
   - Extract reporting code to separate module

2. **Create portfolio calculation pipeline**:
   ```python
   class PortfolioCalculator:
       def __init__(self, tickers, weights, data_provider):
           self.returns_calc = ReturnsCalculator(data_provider)
           self.risk_calc = RiskCalculator(data_provider)
           self.perf_calc = PerformanceCalculator(data_provider)
   ```

### Phase 5: Testing & Documentation (Week 3-4)
1. **Remove all `if __name__ == "__main__"` blocks**
2. **Create proper test files** in `tests/calculations/`
3. **Add comprehensive docstrings**
4. **Create usage examples** in documentation

## Specific File Actions

### Files to Delete/Merge:
- `sector_calculations/` (empty files)
- Merge duplicate calculation functions

### Files to Split:
- `correlation_portfolio_builder.py` → 3-4 smaller modules
- `portfolio_risk_calculations.py` → core risk + portfolio-specific

### Files to Refactor Completely:
- All factor calculation files (remove DB queries)
- All performance calculation files (use core metrics)

## Migration Strategy

### Step 1: Build New Architecture in calculations_vtwo/
- Create complete new architecture in `calculations_vtwo/` directory
- Implement DataProvider and core modules first
- Build and test thoroughly without touching existing `calculations/` folder
- Existing functionality remains completely unaffected
- **Benefits of V2 Approach:**
  - Zero risk to production code during development
  - Can iterate and test freely in isolated environment
  - Easy to compare old vs new implementations side-by-side
  - Rollback is trivial (just ignore the new folder)

### Step 2: Gradual Migration & Integration
- Update dependent services to optionally use `calculations_vtwo` modules
- Create feature flags or configuration to switch between old/new implementations
- Migrate one calculation type at a time (factors, portfolio, etc.)
- Keep `calculations/` as fallback during transition

### Step 3: Final Transition & Cleanup
- Once all functionality proven in `calculations_vtwo/`, update all imports
- Remove dependencies on old `calculations/` folder
- Eventually deprecate `calculations/` folder (keep for reference initially)
- Final integration testing

## Key Design Principles

### 1. Single Responsibility
Each class/function does ONE thing well

### 2. Dependency Injection
Pass data providers, don't create DB sessions internally

### 3. Consistent Interfaces
All calculators follow same pattern:
```python
calculator = SomeCalculator(data_provider)
result = calculator.calculate(ticker, start_date, end_date)
```

### 4. Standardized Output
All calculations return Pydantic models or DataFrames, never raw dicts

### 5. Configuration Management
```python
# constants.py
TRADING_DAYS = 252
DEFAULT_RISK_FREE_RATE = 0.04
DEFAULT_CONFIDENCE_LEVEL = 0.95
```

## Success Metrics

### Code Quality
- ✅ Zero duplicate implementations
- ✅ All files < 300 lines
- ✅ 100% consistent data access
- ✅ Proper error handling throughout

### Performance
- ✅ Optimized database queries through unified data access
- ✅ Faster calculation execution
- ✅ Memory-efficient data handling

### Maintainability
- ✅ Clear module boundaries
- ✅ Easy to add new calculations
- ✅ Simple to modify existing calculations
- ✅ Comprehensive test coverage

## Priority Order

1. **URGENT**: Fix data retrieval inconsistency (blocks everything else)
2. **HIGH**: Eliminate calculation duplication (major technical debt)
3. **MEDIUM**: Refactor portfolio calculations (complex but isolated)
4. **LOW**: Add comprehensive testing (important but not blocking)

## Estimated Timeline

- **Week 1**: Data layer + core calculations
- **Week 2**: Factor refactoring
- **Week 3**: Portfolio refactoring
- **Week 4**: Testing, documentation, cleanup

Total: **4 weeks** for complete refactoring

## Risk Mitigation

1. **Keep old code during migration** - don't break existing functionality
2. **Test each component independently** before integration
3. **Use feature flags** to switch between old/new implementations
4. **Monitor performance** to ensure no regressions
5. **Document all breaking changes** for dependent code

## Next Immediate Actions

1. Create `calculations_vtwo/` directory structure
2. Create `calculations_vtwo/data/data_provider.py` with unified interface
3. Create `calculations_vtwo/core/returns.py` and consolidate all returns calculations
4. Create comprehensive test for returns calculations
5. Migrate one factor (suggest starting with momentum) to new architecture in `calculations_vtwo/factors/`
6. Validate approach before proceeding with full refactoring
