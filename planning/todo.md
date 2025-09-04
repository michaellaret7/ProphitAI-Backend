# Migration to Centralized Calculations V2 Folder

## Overview
This document identifies all places in the codebase that need to be migrated from the old `calculations/` folder to the new centralized `calculations_v2/` folder.

## 1. Direct Imports from Old Calculations Folder

### Factor Calculations
1. **`backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cio/cio_tools.py`**
   - Lines 2-6: Imports from old factor calculations (Growth, Momentum, Quality, Value, Volatility)
   - Line 20: Imports `get_upside_downside_ratios` from old portfolio performance calculations

2. **`backend/src/agentic_framework/base_agent/base_tools/data_wrapper_tool.py`**
   - Lines 4-9: Imports all factor calculations from old folder
   - Lines 357-359: Uses old factor classes in `run_all()` method

### Tool Registries
7. **`backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cro/cro_tool_registry.py`**
   - Line 3: Imports `get_upside_downside_ratios` from old folder

8. **`backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cio/cio_tool_registry.py`**
   - Line 3: Imports `get_upside_downside_ratios` from old folder


## 2. Duplicate Implementations That Should Use Calculations V2

### Correlation and Covariance Calculations
~~9. **`backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cro/cro_tools.py`**~~
    - ~~Lines 54-95: `calculate_correlation_matrix()` function~~
    - ~~Lines 97-138: `calculate_covariance_matrix()` function~~
    - ~~These duplicate functionality in `calculations_v2/risk/calculator.py` and `calculations_v2/portfolio/correlation.py`~~

~~10. **`backend/src/stress_test/pairwise_corr_analysis.py`**~~
    - ~~Lines 7-34: `calculate_correlation_matrix()` function~~
    - ~~Lines 36-56: `pairwise_correlation_analysis()` function~~
    - ~~Similar functionality exists in calculations_v2~~

### Risk Calculations
~~11. **`backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cro/cro_tools.py`**~~
    - ~~Lines 173-372: `vol_es()` function - VaR and Expected Shortfall calculations~~
    - ~~Lines 286-373: `risk_contribution()` function - risk attribution analysis~~
    - ~~Lines 374-489: `drawdown_profile()` function - drawdown analysis~~
    - ~~All these duplicate functionality in calculations_v2/risk/calculator.py~~

### Beta Calculations
~~12. **`backend/src/stress_test/engine.py`**~~
    - ~~Lines 9-41: `calculate_beta_from_data()` function~~
    - ~~Similar functionality exists in calculations_v2/risk/calculator.py for beta calculation~~
    - ~~Completed: engine now uses `calculations_v2.risk.RiskCalculator.beta`; local helper removed~~

## 4. Services With Custom Calculation Implementations

16. **`backend/src/services/prophit_alts_service.py`**
    - Lines 180-186: Custom sharpe_ratio and sortino_ratio calculations
    - Lines 192-195: Custom max_drawdown calculation
    - Lines 202-205: Custom beta calculation
    - These should use calculations_v2 standardized implementations

## 7. Configuration and Support Files

19. **`file_structure.md`** - May need updates to reflect new calculation structure

## Migration Priority Order

### Phase 1: Core Dependencies (High Priority)
- CRO tools (items #9, #11) - critical for fund management
- CIO tools (items #1, #7, #8) - core investment tools
- Data wrapper tools (item #2) - used by agent framework

### Phase 2: Portfolio Optimization (Medium Priority)  
- Phase one formatting (item #5) - user-facing portfolio features
- Phase two metrics and filters (items #3, #4, #6) - screening and analysis

### Phase 3: Services and Support Systems (Lower Priority)
- Services with custom calculations (item #16) - replace with standardized implementations
- Stress test implementations (items #10, #12) - can be updated after core migration
- Error memory references (item #17) - update after tool migration

## Notes
- The `calculations_v2/` folder already has equivalent or superior implementations for most functionality
- Focus on updating imports and replacing duplicate implementations
- Test thoroughly after each phase to ensure functionality is preserved
- Consider deprecating old calculation classes after successful migration