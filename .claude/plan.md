# Fix: Trading Days vs Calendar Days Confusion

## Problem Summary

Two distinct issues exist in the codebase:

### Issue 1: Using trading days (252) with `timedelta()`
`timedelta(days=X)` expects calendar days, but some code passes trading day constants:
- `timedelta(days=252)` = ~8 months back (not 1 year)
- `timedelta(days=756)` = ~2 years back (not 3 years)

### Issue 2: Using calendar days (365) for annualization
Annualization factors should use 252 (trading days per year), not 365:
- `daily_vol * sqrt(365)` overstates annual vol by ~20%
- Correct: `daily_vol * sqrt(252)`

---

## Key Distinction

| Context | Correct Value | Why |
|---------|---------------|-----|
| `timedelta(days=X)` | **365** per year | Calendar days for date math |
| Annualization (vol, returns) | **252** per year | Trading days (data frequency) |
| Rolling window on daily data | **252** for 1 year | Number of data points |

---

## Implementation Steps

### Step 1: Fix annualization bug in RiskCalculator (CRITICAL)

**File:** `app/core/calculations/risk/calculator.py`

Line 75 - Change:
```python
def annualized_volatility(daily_returns: pd.Series, trading_days: int = 365) -> float:
```
To:
```python
def annualized_volatility(daily_returns: pd.Series, trading_days: int = 252) -> float:
```

**Why:** This is using 365 for the annualization factor, which overstates volatility by sqrt(365/252) ≈ 1.20 (20% too high).

---

### Step 2: Update config.py constants

**File:** `app/core/calculations/core/config.py`

Change:
```python
# Standard lookback periods (in trading days)
DEFAULT_LOOKBACK_SHORT: int = 252
DEFAULT_LOOKBACK_MEDIUM: int = 504
DEFAULT_LOOKBACK_LONG: int = 756
```

To:
```python
# Standard lookback periods (in calendar days for use with timedelta)
DEFAULT_LOOKBACK_1Y: int = 365     # 1 year
DEFAULT_LOOKBACK_2Y: int = 730     # 2 years
DEFAULT_LOOKBACK_3Y: int = 1095    # 3 years
```

Update `__all__` exports accordingly.

---

### Step 3: Fix the actual timedelta bug in alts.py

**File:** `app/services/alts/alts.py`

This file uses `DEFAULT_LOOKBACK_LONG` (756) directly with `timedelta()` WITHOUT conversion.

Line 7 - Update import:
```python
from app.core.calculations.core.config import DEFAULT_LOOKBACK_3Y
```

Line 30 - Update default:
```python
def __init__(self, fund_name: str, lookback_days: int = DEFAULT_LOOKBACK_3Y, frequency: str = 'daily'):
```

Line 89 stays the same (now correct since `lookback_days` will be calendar days).

---

### Step 4: Simplify files that already do conversion

These files correctly do `* 365 / 252` conversion - simplify them to use new constants:

| File | Line | Current Code | New Code |
|------|------|--------------|----------|
| `app/services/alts/correlation.py` | 9, 51 | Import `DEFAULT_LOOKBACK_SHORT`, use `int(DEFAULT_LOOKBACK_SHORT * 365 / 252)` | Import `DEFAULT_LOOKBACK_1Y`, use `DEFAULT_LOOKBACK_1Y` |
| `app/core/calculations/portfolio/correlation.py` | 175, 180 | Import `DEFAULT_LOOKBACK_LONG`, use `int(DEFAULT_LOOKBACK_LONG * 365 / 252)` | Import `DEFAULT_LOOKBACK_3Y`, use `DEFAULT_LOOKBACK_3Y` |
| `app/core/calculations/sectors/base.py` | 136, 138, 165, 167 | Import `DEFAULT_LOOKBACK_LONG`, use `int(DEFAULT_LOOKBACK_LONG * 365 / 252)` | Import `DEFAULT_LOOKBACK_3Y`, use `DEFAULT_LOOKBACK_3Y` |

---

### Step 5: Update files that pass lookback_days to functions that convert

These files pass `DEFAULT_LOOKBACK_*` to functions that internally convert. Update imports:

| File | Import Change |
|------|---------------|
| `app/utils/decorators/price_data.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/ticker_tools/performance.py` | `DEFAULT_LOOKBACK_MEDIUM` → `DEFAULT_LOOKBACK_2Y` |
| `app/core/agentic_framework/tool_lib/ticker_tools/weekly_returns.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/risk_tools/drawdown_profile.py` | `DEFAULT_LOOKBACK_LONG` → `DEFAULT_LOOKBACK_3Y` |
| `app/core/agentic_framework/tool_lib/risk_tools/asset_risk_contrib.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/risk_tools/pairwise_corr_analysis.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/corr_matrix.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/risk_tools/cov_matrix.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/risk_tools/vol_es.py` | `DEFAULT_LOOKBACK_SHORT` → `DEFAULT_LOOKBACK_1Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/performance.py` | `DEFAULT_LOOKBACK_LONG` → `DEFAULT_LOOKBACK_3Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/ticker_performance.py` | `DEFAULT_LOOKBACK_MEDIUM` → `DEFAULT_LOOKBACK_2Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/returns.py` | `DEFAULT_LOOKBACK_LONG` → `DEFAULT_LOOKBACK_3Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/group_performance.py` | `DEFAULT_LOOKBACK_LONG` → `DEFAULT_LOOKBACK_3Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/beta.py` | `DEFAULT_LOOKBACK_MEDIUM` → `DEFAULT_LOOKBACK_2Y` |
| `app/core/agentic_framework/tool_lib/portfolio_tools/build_allocations.py` | `DEFAULT_LOOKBACK_LONG` → `DEFAULT_LOOKBACK_3Y` |

---

### Step 6: Remove conversion code in utility functions

These functions currently convert trading days to calendar days. After the constant rename, they should accept calendar days directly:

| File | Line | Change |
|------|------|--------|
| `app/core/calculations/portfolio/utils.py` | 39 | Remove `* 365 / 252` conversion |
| `app/core/calculations/portfolio/utils.py` | 160 | Remove `* 365 / 252` conversion |
| `app/utils/decorators/price_data.py` | 27 | Remove `* 365 / 252` conversion |
| `app/utils/decorators/price_data.py` | 64 | Remove `* 365 / 252` conversion |
| `app/core/calculations/portfolio/allocations/optimizer.py` | 116 | Remove `* 365 / 252` conversion |
| `app/core/calculations/portfolio/allocations/allocator.py` | 155 | Remove `* 365 / 252` conversion |
| `app/utils/simulation_utils.py` | 62 | Remove `* 365 / 252` conversion |

---

## Files Changed Summary

| File | Change Type |
|------|-------------|
| `app/core/calculations/risk/calculator.py` | **Fix annualization bug** (365→252) |
| `app/core/calculations/core/config.py` | Rename constants to calendar days |
| `app/services/alts/alts.py` | Update import + fix timedelta bug |
| `app/services/alts/correlation.py` | Update import + simplify |
| `app/core/calculations/portfolio/correlation.py` | Update import + simplify |
| `app/core/calculations/sectors/base.py` | Update import + simplify |
| `app/core/calculations/portfolio/utils.py` | Remove conversion code |
| `app/utils/decorators/price_data.py` | Update import + remove conversion |
| `app/core/calculations/portfolio/allocations/optimizer.py` | Remove conversion code |
| `app/core/calculations/portfolio/allocations/allocator.py` | Remove conversion code |
| `app/utils/simulation_utils.py` | Remove conversion code |
| 14 tool files in `app/core/agentic_framework/tool_lib/` | Update imports |

---

## What NOT to Change

- `DEFAULT_TRADING_DAYS = 252` - correct for annualization factors
- `trading_days=252` parameters in annualization functions - correct
- `np.sqrt(252)` for volatility annualization - correct
- `rolling(window=252)` calls - correct (252 data points = ~1 year of trading data)
- `* 252` for return annualization - correct

---

## Notebooks (Lower Priority - Separate PR)

| File | Line | Issue |
|------|------|-------|
| `notebooks/sma_strategy.ipynb` | 337 | Uses `365**0.5` for vol annualization (should be 252) |

---

## Verification

After implementation:
1. Run the test code to confirm date ranges are correct:
```python
end_date = datetime.now()
start_date = end_date - timedelta(days=365)
# Should show exactly 1 year back
```

2. Verify annualized volatility calculation:
```python
# For daily returns, annual_vol = daily_vol * sqrt(252)
# NOT daily_vol * sqrt(365)
```
