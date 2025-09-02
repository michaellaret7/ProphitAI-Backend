# Implementation Plan: Correlation Portfolio Builder v2

## Overview
Create a new correlation-aware portfolio builder module that fully leverages the calculations_v2 folder's clean, modular architecture. This implementation will replace the old build_corr_portfolio module with a more maintainable and efficient version.

## Phase 1: Core Architecture Setup

### 1.1 Directory Structure
```
backend/src/calculations_v2/portfolio/
├── __init__.py (update existing)
├── correlation.py (existing - extend)
└── build/
    ├── __init__.py (new - exports builder classes)
    ├── builder.py (new - main orchestrator)
    ├── optimizer.py (new - optimization logic)
    ├── reporter.py (new - reporting utilities)
    └── visualizer.py (new - visualization tools)
```

### 1.2 Key Design Principles
- **Single Responsibility**: Each module handles one specific aspect
- **Dependency Injection**: Use DataService for all data fetching
- **Type Safety**: Use Pydantic models from core/models.py
- **DRY Principle**: Reuse existing calculators from calculations_v2
- **Clean Interfaces**: Clear input/output contracts between modules
- **Organized Structure**: Build-related modules isolated in dedicated subfolder for clarity

### 1.3 Import Structure Example
```python
# From outside the portfolio module:
from backend.src.calculations_v2.portfolio.build import (
    CorrelationPortfolioBuilder,
    PortfolioOptimizer,
    PortfolioReporter,
    PortfolioVisualizer
)

# Or import the entire build module:
from backend.src.calculations_v2.portfolio import build

# Usage:
builder = build.CorrelationPortfolioBuilder(data_service)
```

## Phase 2: Module Implementation Plan

### 2.1 Extend portfolio/correlation.py
**Current State**: Already has CorrelationAnalysis class with basic correlation utilities
**Extensions Needed**:
- Add portfolio-specific correlation metrics
- Add risk contribution analysis methods
- Leverage existing RiskCalculator methods

```python
# Key methods to add:
- effective_diversification_ratio()
- concentration_risk_metrics()
- correlation_risk_contribution()
```

### 2.2 Create portfolio/build/optimizer.py
**Purpose**: Portfolio weight optimization logic
**Dependencies**:
- Use RiskCalculator for VaR, volatility calculations
- Use CorrelationAnalysis for correlation matrices
- Use existing covariance_matrix from RiskCalculator

**Key Components**:
```python
class PortfolioOptimizer:
    - optimize_weights_risk_parity()
    - optimize_weights_min_variance()
    - optimize_weights_max_sharpe()
    - apply_constraints()
    - calculate_position_sizes()
```

### 2.3 Create portfolio/build/builder.py
**Purpose**: Main orchestrator that combines all components
**Dependencies**:
- DataService for data fetching (replace old DataFetcher)
- ReturnsCalculator for return calculations
- RiskCalculator for risk metrics
- PerformanceCalculator for performance metrics
- PortfolioOptimizer for optimization
- CorrelationAnalysis for correlation metrics

**Key Components**:
```python
class CorrelationPortfolioBuilder:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.returns_calc = ReturnsCalculator()
        self.risk_calc = RiskCalculator()
        self.perf_calc = PerformanceCalculator()
        self.optimizer = PortfolioOptimizer()
        
    - build_portfolio()
    - fetch_and_prepare_data()
    - calculate_optimal_weights()
    - generate_risk_metrics()
    - create_portfolio_report()
```

### 2.4 Create portfolio/build/reporter.py
**Purpose**: Generate comprehensive portfolio reports
**Dependencies**:
- Use existing performance metrics from PerformanceCalculator
- Use risk metrics from RiskCalculator

**Key Components**:
```python
class PortfolioReporter:
    - generate_summary_report()
    - generate_risk_report()
    - generate_performance_report()
    - generate_correlation_report()
    - export_to_json()
    - export_to_dataframe()
```

### 2.5 Create portfolio/build/visualizer.py
**Purpose**: Portfolio visualization utilities
**Dependencies**:
- matplotlib/plotly for visualizations
- Use correlation matrices from CorrelationAnalysis

**Key Components**:
```python
class PortfolioVisualizer:
    - plot_correlation_heatmap()
    - plot_risk_contribution()
    - plot_efficient_frontier()
    - plot_portfolio_composition()
    - plot_performance_metrics()
```

## Phase 3: Migration Strategy

### 3.1 Data Flow Refactoring
**Old Flow**:
```
DataFetcher → ReturnsCalculator → CorrelationAnalyzer → PortfolioOptimizer
```

**New Flow**:
```
DataService → ReturnsCalculator/RiskCalculator → CorrelationAnalysis/PortfolioOptimizer → Reporter/Visualizer
```

### 3.2 Key Replacements
| Old Component | New Component | Benefits |
|--------------|---------------|----------|
| DataFetcher | DataService | Centralized caching, consistent interface |
| Custom returns calc | ReturnsCalculator | Standardized, tested utilities |
| Custom risk metrics | RiskCalculator | Comprehensive risk calculations |
| Custom performance | PerformanceCalculator | Full suite of performance metrics |
| Embedded correlation | CorrelationAnalysis | Modular, reusable correlation utilities |

### 3.3 Method Mapping
- `fetch_price_data()` → `DataService.get_bulk_close_series()`
- `calculate_returns()` → `ReturnsCalculator.daily_price_returns()`
- `calculate_correlation_matrix()` → `CorrelationAnalysis.correlation_matrix()`
- `calculate_portfolio_volatility()` → `RiskCalculator.annualized_volatility()`
- `calculate_var()` → `RiskCalculator.monte_carlo_var()`
- `calculate_sharpe_ratio()` → `PerformanceCalculator.sharpe_ratio()`

## Phase 4: Implementation Steps

### Step 1: Core Module Setup
1. Create portfolio/build/ directory structure
2. Create portfolio/build/__init__.py to export builder classes
3. Extend portfolio/__init__.py to export build module
4. Extend correlation.py with portfolio-specific methods
5. Create base structure for build/optimizer.py

### Step 2: Builder Implementation
1. Create build/builder.py with main orchestration logic
2. Implement data fetching using DataService
3. Wire up calculations using existing calculators

### Step 3: Optimizer Implementation
1. Port optimization algorithms to build/optimizer.py
2. Implement constraint handling
3. Add position sizing logic

### Step 4: Reporting & Visualization
1. Create build/reporter.py with reporting logic
2. Create build/visualizer.py with plotting functions
3. Ensure compatibility with existing output formats

### Step 5: Testing & Validation
1. Create unit tests for each new module
2. Compare outputs with old implementation
3. Performance benchmarking

## Phase 5: Code Quality Requirements

### 5.1 Standards
- Type hints for all methods
- Docstrings following Google style
- Error handling with custom exceptions
- Input validation using Pydantic models

### 5.2 Performance Optimizations
- Leverage DataService caching
- Use vectorized operations (numpy/pandas)
- Minimize redundant calculations
- Parallel processing where applicable

### 5.3 Testing Strategy
- Unit tests for each module
- Integration tests for full workflow
- Performance regression tests
- Output validation against old implementation

## Phase 6: Benefits of New Implementation

### 6.1 Immediate Benefits
- **Modularity**: Each component can be used independently
- **Maintainability**: Clear separation of concerns
- **Reusability**: Leverages existing tested calculators
- **Performance**: Built-in caching from DataService
- **Consistency**: Uses standardized data models

### 6.2 Future Benefits
- **Extensibility**: Easy to add new optimization methods
- **Testability**: Modular design enables comprehensive testing
- **Documentation**: Clear interfaces simplify documentation
- **Integration**: Fits seamlessly with calculations_v2 ecosystem

## Implementation Priority

1. **High Priority** (Core Functionality)
   - Create portfolio/build/ directory structure
   - build/builder.py (orchestrator)
   - build/optimizer.py (weight optimization)
   - build/__init__.py (module exports)
   - Extend correlation.py

2. **Medium Priority** (Enhanced Features)
   - build/reporter.py (reporting)
   - Advanced optimization methods

3. **Low Priority** (Nice to Have)
   - build/visualizer.py (visualization)
   - Additional performance metrics

## Success Criteria

- [ ] All existing functionality preserved
- [ ] Performance equal or better than old implementation
- [ ] Full test coverage (>90%)
- [ ] Clean separation of concerns
- [ ] No code duplication
- [ ] Comprehensive error handling
- [ ] Type safety throughout
- [ ] Documentation complete

## Notes

- The new implementation should be backwards compatible with existing API contracts
- Consider creating a migration script for smooth transition
- Ensure all dependencies are properly managed
- Follow the established patterns in calculations_v2

## Step-by-Step Implementation Plan

### STEP 1: Create Directory Structure
1. Navigate to `backend/src/calculations_v2/portfolio/`
2. Create new directory: `build/`
3. Create empty `__init__.py` files in build folder
4. Verify structure with `tree` command

### STEP 2: Set Up Base Files (Empty Templates)
1. Create `portfolio/build/__init__.py` with module exports template
2. Create `portfolio/build/builder.py` with class skeleton
3. Create `portfolio/build/optimizer.py` with class skeleton

### STEP 3: Implement Data Integration Layer
1. In `build/builder.py`:
   - Import DataService from core
   - Import ReturnsCalculator, RiskCalculator, PerformanceCalculator
   - Create `__init__` method with DataService injection
   - Implement `fetch_and_prepare_data()` method using DataService.get_bulk_close_series()
   - Create data validation methods

### STEP 4: Port Returns Calculations
1. In `build/builder.py`:
   - Replace old returns calculation with ReturnsCalculator.daily_price_returns()
   - Implement returns DataFrame assembly
   - Add returns data caching logic
   - Test returns calculation matches old implementation

### STEP 5: Extend Correlation Module
1. In `portfolio/correlation.py`:
   - Add `effective_diversification_ratio()` method
   - Add `concentration_risk_metrics()` method  
   - Add `correlation_risk_contribution()` method
   - Ensure all methods leverage RiskCalculator base methods
   - Write unit tests for new methods

### STEP 6: Implement Portfolio Optimizer
1. In `build/optimizer.py`:
   - Import numpy, pandas, scipy.optimize
   - Import RiskCalculator and CorrelationAnalysis
   - Port `optimize_weights_risk_parity()` from old implementation
   - Port `optimize_weights_min_variance()` from old implementation
   - Port `optimize_weights_max_sharpe()` from old implementation
   - Implement `apply_constraints()` method
   - Implement `calculate_position_sizes()` method
   - Replace old VaR calculations with RiskCalculator.monte_carlo_var()

### STEP 7: Build Main Orchestrator
1. In `build/builder.py`:
   - Complete `CorrelationPortfolioBuilder` class
   - Implement `build_portfolio()` main method
   - Wire up optimizer integration
   - Add `calculate_optimal_weights()` method calling optimizer
   - Implement `generate_risk_metrics()` using RiskCalculator
   - Add error handling and validation

### STEP 9: Update Module Exports
1. Update `portfolio/build/__init__.py`:
   ```python
   from .builder import CorrelationPortfolioBuilder
   from .optimizer import PortfolioOptimizer
   from .reporter import PortfolioReporter
   from .visualizer import PortfolioVisualizer
   
   __all__ = [
       'CorrelationPortfolioBuilder',
       'PortfolioOptimizer', 
       'PortfolioReporter',
       'PortfolioVisualizer'
   ]
   ```
2. Update `portfolio/__init__.py` to export build module

### VERIFICATION CHECKLIST
- [ ] Directory structure created correctly
- [ ] All imports resolve without errors
- [ ] DataService integration working
- [ ] Returns calculations match old implementation
- [ ] Risk calculations use RiskCalculator
- [ ] Performance metrics use PerformanceCalculator  
- [ ] Correlation analysis uses CorrelationAnalysis
- [ ] Optimizer produces valid weights
- [ ] Reports generate successfully
- [ ] Visualizations render correctly
- [ ] All tests pass
- [ ] Performance is equal or better
- [ ] Documentation is complete
- [ ] No code duplication
- [ ] Follows calculations_v2 patterns
