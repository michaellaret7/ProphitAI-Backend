# COMPREHENSIVE ARCHITECTURAL ANALYSIS: DATA FETCHING PATTERNS

**Date:** 2025-10-22
**Status:** Critical Technical Debt Identified
**Priority:** High - Refactoring Recommended

---

## EXECUTIVE SUMMARY

The codebase has **significant architectural complexity and multiple violations of KISS/DRY/YAGNI principles**. There are at least **3-4 distinct data fetching paths** for the same data types, inconsistent abstraction patterns, and coupling issues between layers.

**Verdict: YES, Data Fetching is Too Convoluted** ❌

---

## 1. DATA FLOW ARCHITECTURE MAP

### Layer 1: Repository Layer (Source of Truth)
**File:** `/Users/michaellaret/Desktop/ProphitAI/app/repositories/`

This layer directly queries the database and is the primary data source:

#### Price Data Repository
- **File:** `price_data.py`
- **Functions:**
  - `get_price_data_15_mins(ticker, start_date, end_date)` - 15-minute candles
  - `get_price_data_hourly(ticker, start_date, end_date)` - Resampled hourly
  - `get_price_data_daily(ticker, start_date, end_date)` - Daily OHLCV (efficient SQL aggregation)
  - `fetch_bulk_price_data_for_tickers(tickers, start_date_str, end_date_str, frequency)` - **PRIMARY BULK FETCH** with ThreadPoolExecutor (20 workers)
  - `fetch_bulk_ohlcv_data_for_tickers(tickers, start_date_str, end_date_str)` - Full DataFrame OHLCV
  - `get_dividends_series(ticker, start_date, end_date)` - Dividend data

#### Fundamental Data Repository
- **File:** `fundamental_data.py`
- **Functions:**
  - `get_fundamental_data(ticker, statement_type, quarters_back, _simulation_date)` - Routes to 5 statement types
  - `get_all_fundamentals(ticker, quarters_back)` - Fetches all 5 types at once

#### Other Repositories
- `etf_data.py`: `get_etf_info()`, `get_etf_holdings()`
- `news_data.py`: `get_press_releases()`, `get_stock_news()`, `get_price_target_news()`
- `ratings_data.py`: `get_stock_grades_individual()`, `get_stock_grades_summary()`, `get_ratings()`, `get_analyst_recommendations()`, `get_price_target_summary()`
- `portfolio_data.py`: `retrieve_portfolio()`, `add_portfolio()`, etc. (user-specific data)
- `transcripts_data.py`: Earnings transcripts

---

### Layer 2: Service Layer (Data Abstraction & Caching)
**File:** `/Users/michaellaret/Desktop/ProphitAI/app/core/calculations/core/data_service.py`

**Class:** `DataService`

This layer sits between repositories and calculations, adding **in-memory caching** with simple dict-based cache:

```python
- _price_cache: Dict[tuple[str, datetime, datetime], pd.DataFrame]
- _div_cache: Dict[tuple[str, datetime, datetime], pd.Series]
- _fund_cache: Dict[str, FundamentalData]
```

**Methods:**
- `get_price_data(ticker, start_date, end_date)` → Wraps `get_price_data_daily()` with caching
- `get_bulk_close_series(tickers, start_date, end_date)` → Calls `fetch_bulk_price_data_for_tickers()`
- `get_dividends(ticker, start_date, end_date)` → Direct DB query with caching
- `get_fundamentals(ticker)` → Direct DB query with caching
- `get_bulk_fundamentals(tickers, max_workers=8)` → Parallel fetching with caching

---

### Layer 3: Calculations Layer (Data Transformation & Analysis)
**Directory:** `/Users/michaellaret/Desktop/ProphitAI/app/core/calculations/`

#### 3A: Core Helpers
**File:** `core/helpers.py`

**Key functions:**
- `build_returns_df_for_dates(tickers, start_date, end_date, include_dividends, drop_rows)` - **CRITICAL PATH**
  - Calls `fetch_bulk_price_data_for_tickers()` directly (BYPASSES DataService!)
  - Calls `get_dividends_series()` directly from repository
  - This is used by portfolio concentration calculations

- `build_returns_df_from_price_map(price_map, drop_rows, include_dividends, dividends_map)` - Generic builder

**Support utilities:**
- `filter_rows_by_cutoff_date()`, `winsorize_series()`, `zscore_series()`, `safe_divide()`, etc.

#### 3B: Portfolio Utilities
**File:** `portfolio/utils.py`

**Functions:**
- `prepare_portfolio_data(portfolio, lookback_days, include_dividends, include_benchmark, _simulation_date)` - **LAYER BRIDGE**
  - Creates DataService instance
  - Calls `ds.get_bulk_close_series()` (DataService)
  - Calls `ds.get_dividends()` (DataService)

- `get_portfolio_returns(portfolio, lookback_days, use_total_returns, dropna, _simulation_date)`
  - Calls `prepare_portfolio_data()` which uses DataService

- `get_benchmark_returns(benchmark, start, end, lookback_days, use_total_returns, _simulation_date)`
  - Creates DataService instance
  - Calls `ds.get_bulk_close_series()`
  - Calls `ds.get_dividends()`

#### 3C: Factor Calculations
**Directory:** `factors/`
- `growth.py`, `value.py`, `quality.py`, `momentum.py`, `volatility.py`
- These fetch fundamental data via DataService and price data

#### 3D: Portfolio Concentration
**File:** `portfolio/concentration.py`

**Class:** `PortfolioConcentration`

```python
def __init__(self, portfolio_dict, start_date, end_date, confidence):
    # Fetches ticker metadata via MarketSession directly (DB coupling!)
    session = MarketSession()
    rows = session.query(Ticker).filter(Ticker.ticker.in_(self.tickers)).all()

def _var_grouped(self, label_map):
    # CALLS build_returns_df_for_dates() which bypasses DataService!
    returns_df = build_returns_df_for_dates(
        self.tickers, self.start_date, self.end_date,
        include_dividends=False, drop_rows='any'
    )
```

---

### Layer 4: Tool Layer (Agent Interface)
**Directory:** `/Users/michaellaret/Desktop/ProphitAI/app/core/agentic_framework/tool_lib/`

#### 4A: Data Fetching Tools
**File:** `data_tools/repository.py`

**Function:** `fetch_repository_data(ticker, data_type, limit, _simulation_date)` - **ROUTER**

Routes to various repository functions:
- News: `get_press_releases()`, `get_stock_news()`, `get_price_target_news()`
- Ratings: `get_stock_grades_individual()`, `get_stock_grades_summary()`, `get_ratings()`, `get_analyst_recommendations()`, `get_price_target_summary()`
- ETF: `get_etf_info()`, `get_etf_holdings()`
- Transcripts: `get_earnings_transcripts()`, `get_latest_transcript()`
- Dividends: `get_dividends_series()`

#### 4B: Fundamental Data Tools
**File:** `data_tools/ticker_fundamentals.py`

**Function:** `get_fundamental_data(ticker, statement_type, quarters_back, _simulation_date)`
- Wraps `fundamental_data.get_fundamental_data()` and returns YAML

#### 4C: Portfolio Analysis Tools
**Files:** `portfolio_tools/*.py`

**Key tools:**
- `returns.py`: `calculate_portfolio_returns_metrics()`
  - Calls `get_portfolio_returns()` from calculations.portfolio.utils
  - Uses `ReturnsCalculator` classes

- `ticker_performance.py`: `calculate_ticker_performances()`
  - Calls `prepare_portfolio_data()` from calculations
  - Uses performance calculators

- `concentration.py`: `exposure_calculator()`, `industry_concentration()`, `VaR_calculator()`
  - Uses `PortfolioConcentration` class

- `cov_matrix.py`: `calculate_covariance_matrix()`
  - Calls `prepare_portfolio_data()`
  - Calls `build_returns_df_from_price_map()`

#### 4D: Ticker Analysis Tools
**Files:** `ticker_tools/*.py`

- `performance.py`: `get_ticker_performance_and_risk()`
  - Uses decorator `@with_bulk_price_data()` to fetch price data
  - Creates DataService instance
  - Calls `ds.get_price_data()` (DataService)
  - Calls `ds.get_dividends()` (DataService)

- `factors.py`: `calculate_ticker_factors()`
  - Creates DataService instance
  - Calls `ds.get_price_data()` (DataService)

- `weekly_returns.py`, `performance.py`: Various ticker-specific metrics

#### 4E: Agent-Specific Tools
**Files:** `agent_specific_tools/*.py`

- `cio.py`: `get_analyst_picks()`
- `cro.py`: `get_final_portfolio_dict()`
- `industry.py`: `get_eligible_tickers()`, `get_base_ticker_info()`
- `optimizer.py`: `get_user_portfolio()`

---

## 2. COMPLEXITY INDICATORS & VIOLATIONS

### 2.1 Multiple Paths for Price Data Fetching

**Path 1: Repository Direct (Used by PortfolioConcentration)**
```
build_returns_df_for_dates()
  → fetch_bulk_price_data_for_tickers() (repository)
  → get_dividends_series() (repository)
```

**Path 2: DataService (Used by tools)**
```
Tool → DataService.get_bulk_close_series()
  → fetch_bulk_price_data_for_tickers()
DataService.get_dividends()
  → Direct DB query (bypasses repository caching)
```

**Path 3: Decorator-Based (Used by ticker_performance.py)**
```
@with_bulk_price_data() decorator
  → Tool receives pre-fetched price_data dict
  → But still creates DataService for fallback/SPY
```

**Path 4: Direct Repository (Used inconsistently)**
```
Tool → repository.get_price_data_daily() (without bulk/threading)
```

**VIOLATION:** DRY - Same data fetched 4 different ways. KISS - Unnecessary complexity.

### 2.2 Redundant Data Fetching Functions

**Price Data (5 functions for similar purpose):**
1. `get_price_data_15_mins()` - 15-min candles
2. `get_price_data_hourly()` - Resamples 15-min to hourly
3. `get_price_data_daily()` - Daily OHLCV
4. `fetch_bulk_price_data_for_tickers()` - Bulk parallel daily
5. `fetch_bulk_ohlcv_data_for_tickers()` - Bulk parallel full OHLCV

**Issue:** `fetch_bulk_price_data_for_tickers()` has a `frequency` parameter but CLAUDE.md says "ALWAYS use this function" - yet other functions still exist and are used in some places.

**VIOLATION:** YAGNI - 15-min and hourly functions exist but are never used in tools/calculations (only daily is used).

### 2.3 Inconsistent Abstraction Patterns

**DataService Pattern (Recommended):**
```python
# Correct: Tools should use DataService
ds = DataService()
prices = ds.get_bulk_close_series(tickers, start, end)
divs = ds.get_dividends(ticker, start, end)
```

**Direct Repository Pattern (Inconsistent):**
```python
# Wrong: PortfolioConcentration bypasses DataService
returns_df = build_returns_df_for_dates(
    tickers, start_date, end_date,  # Direct to repository!
    include_dividends=False
)
```

**Direct DB Pattern (Severe violation):**
```python
# Wrong: PortfolioConcentration directly queries DB
session = MarketSession()
rows = session.query(Ticker).filter(Ticker.ticker.in_(self.tickers)).all()
```

**VIOLATION:** DRY - Three different patterns coexist. Dependency Inversion violated.

### 2.4 Abstraction Leaks (Business Logic in Repositories)

**Repository `price_data.py`:**
- `get_price_data_hourly()` has BUSINESS LOGIC:
  ```python
  ohlc_dict = {
      'open': 'first',
      'high': 'max',
      'low': 'min',
      'close': 'last',
      'volume': 'sum'
  }
  hourly_data_df = data_15_min_df.resample('h').apply(ohlc_dict)
  ```
  Should be in calculations layer, not repository!

**Fundamental Data Repository `fundamental_data.py`:**
- Line 105-108: **Field extraction logic** (building dicts) should be in service layer
  ```python
  "working_capital": float(stmt.totalCurrentAssets - stmt.totalCurrentLiabilities)
      if (hasattr(...) and ...) else None,
  ```
  This is calculation, not data fetching!

**VIOLATION:** Single Responsibility - Repositories have extraction/transformation logic.

### 2.5 Coupling Issues

**Tight Coupling Example 1: PortfolioConcentration**
```python
# In portfolio/concentration.py
class PortfolioConcentration:
    def __init__(self, portfolio_dict, start_date=None, end_date=None):
        session = MarketSession()  # Direct DB coupling!
        rows = session.query(Ticker).filter(...).all()
        # Should inject data service or fetch metadata differently
```

**Tight Coupling Example 2: Calculations directly call repository functions**
```python
# In core/helpers.py
def build_returns_df_for_dates(...):
    price_map = fetch_bulk_price_data_for_tickers(...)  # Direct repo!
    dividends_map[t] = get_dividends_series(t, ...)  # Direct repo!
    # Should use DataService!
```

**VIOLATION:** Dependency Inversion - High-level modules depend on low-level repository functions.

### 2.6 Inconsistent Simulation Date Handling

**Inconsistency:** Some functions accept `_simulation_date`, others don't:
- ✓ `prepare_portfolio_data(..., _simulation_date=None)`
- ✓ `get_portfolio_returns(..., _simulation_date=None)`
- ✗ `PortfolioConcentration.__init__(..., end_date=None)` - Uses `end_date` parameter instead of `_simulation_date`
- ✗ `build_returns_df_for_dates()` - NO simulation date support! Can't be used in backtesting

**VIOLATION:** Inconsistency - Same concept named differently across codebase.

### 2.7 Unnecessary Wrapper Functions

**Example: Tool wrapping repository wrapping repository**
```
ticker_fundamentals.py:get_fundamental_data() [TOOL]
  → calls repositories/fundamental_data.py:get_fundamental_data() [REPOSITORY]
    → calls DataService().get_fundamentals() [SERVICE]
      → queries DB directly

This is 3 layers for simple fetching + YAML formatting!
```

**VIOLATION:** KISS & YAGNI - Unnecessary indirection.

### 2.8 Parallel Fetching Inconsistency

**Inconsistent use of ThreadPoolExecutor:**
- ✓ `fetch_bulk_price_data_for_tickers()` - Uses ThreadPoolExecutor(max_workers=20)
- ✓ `DataService.get_bulk_fundamentals()` - Uses ThreadPoolExecutor(max_workers=8)
- ✗ `build_returns_df_for_dates()` - Fetches dividends sequentially in loop!
  ```python
  for t in tickers_norm:  # Sequential!
      divs = get_dividends_series(t, start_date, end_date)
  ```

**VIOLATION:** YAGNI & Performance - Unnecessary sequential fetching when parallel is possible.

---

## 3. SPECIFIC ARCHITECTURAL ISSUES BY AREA

### 3.1 `app/core/agentic_framework/tool_lib/`

**Current State:**
- Tools call repository functions directly ✓ (Some)
- Tools use DataService ✓ (Some)
- Tools use decorators for data injection ✓ (Limited use)
- Tools use helpers that bypass DataService ✗ (PortfolioConcentration)

**Files with Issues:**
1. **`data_tools/repository.py`** - Router with 15+ branches, creates its own output format (YAML)
2. **`portfolio_tools/concentration.py`** - Uses `PortfolioConcentration` which has DB coupling
3. **`portfolio_tools/cov_matrix.py`** - Calls `prepare_portfolio_data()` correctly ✓
4. **`portfolio_tools/returns.py`** - Calls `get_portfolio_returns()` correctly ✓
5. **`ticker_tools/performance.py`** - Uses decorator + DataService correctly ✓
6. **`ticker_tools/factors.py`** - Uses DataService correctly ✓

### 3.2 `app/repositories/`

**Current State:**
- Price data: Good parallel fetching with `fetch_bulk_price_data_for_tickers()`
- Fundamental: No public bulk function, only `DataService.get_bulk_fundamentals()`
- ETF/News/Ratings: Simple query wrappers ✓
- Fundamental: Has calculation logic (working_capital) mixed in ✗

**Design Issues:**
1. Hourly/15-min functions never used (YAGNI)
2. Calculation logic in `fundamental_data.py` (abstraction leak)
3. `get_dividends_series()` called from multiple paths (helper duplicates logic)

### 3.3 `app/core/calculations/`

**Current State:**
- Core helpers call repository directly ✗
- Portfolio utils use DataService ✓
- Risk calculators use shared `build_returns_df_for_dates()` ✓
- `PortfolioConcentration` queries DB directly ✗

**Design Issues:**
1. `build_returns_df_for_dates()` bypasses DataService (no caching benefit)
2. `PortfolioConcentration.__init__()` queries ticker metadata directly
3. No simulation date support in `build_returns_df_for_dates()`
4. Dividend fetching sequential not parallel (line 348-353 in helpers.py)

---

## 4. KISS/DRY/YAGNI VIOLATIONS SUMMARY

### DRY Violations (Duplicate/Repeated Logic)

| Issue | Location | Details |
|-------|----------|---------|
| Price fetch paths | 4 different paths | repository → DataService → decorator → helper |
| Dividend fetching | 2 patterns | `DataService.get_dividends()` vs `get_dividends_series()` (identical) |
| Simulation date handling | Inconsistent naming | `_simulation_date` vs `end_date` parameter |
| Returns calculation | Multiple helpers | `build_returns_df_from_price_map()` + `build_returns_df_for_dates()` + repository utilities |
| Ticker metadata fetch | Direct DB + repository | `PortfolioConcentration` queries directly vs using repository |

### YAGNI Violations (Unused Functionality)

| Function | File | Usage | Status |
|----------|------|-------|--------|
| `get_price_data_15_mins()` | price_data.py | Never used in tools/calculations | REMOVE |
| `get_price_data_hourly()` | price_data.py | Never used in tools/calculations | REMOVE |
| `frequency` parameter (except 'daily') | price_data.py | 15mins/hourly never used | REMOVE |

### KISS Violations (Over-Engineering)

| Issue | Impact |
|-------|--------|
| 3-layer wrapper for fundamentals | Unnecessary indirection |
| Multiple DataService caching patterns | Simple dict cache is enough, but used inconsistently |
| Direct DB queries in Concentration class | Couples business logic to DB layer |
| Parallel + Sequential mixing | Some functions parallel, others sequential (inconsistent) |

---

## 5. DEPENDENCY FLOW DIAGRAM

```
TOOLS (Agent Interface)
    ├─ Portfolio Tools
    │  ├─ calculate_portfolio_returns_metrics() → get_portfolio_returns() ✓ (DataService)
    │  ├─ calculate_ticker_performances() → prepare_portfolio_data() ✓ (DataService)
    │  ├─ calculate_covariance_matrix() → prepare_portfolio_data() ✓ (DataService)
    │  ├─ concentration.py → PortfolioConcentration ✗ (DB Direct)
    │  │                   → build_returns_df_for_dates() ✗ (Repo Direct)
    │  └─ ...
    │
    ├─ Ticker Tools
    │  ├─ performance.py → DataService ✓
    │  ├─ factors.py → DataService ✓
    │  └─ ...
    │
    └─ Data Tools
       ├─ repository.py → Route to repositories ✓
       └─ ticker_fundamentals.py → Repository wrapper (unnecessary) ✗

CALCULATIONS (Business Logic)
    ├─ Portfolio Utils
    │  ├─ prepare_portfolio_data() → DataService ✓
    │  ├─ get_portfolio_returns() → Repository (deprecated path)
    │  └─ ...
    │
    ├─ Concentration (BAD)
    │  └─ PortfolioConcentration → MarketSession ✗ (DB Direct)
    │                             → build_returns_df_for_dates() ✗ (Repo Direct)
    │
    ├─ Core Helpers (BAD)
    │  ├─ build_returns_df_for_dates() → fetch_bulk_price_data_for_tickers() ✗
    │  ├─ build_returns_df_for_dates() → get_dividends_series() ✗
    │  └─ ...
    │
    └─ Factor/Risk/Performance Calculators → Uses helpers (may use bad patterns)

DATA SERVICE (Caching Layer)
    ├─ get_bulk_close_series() → fetch_bulk_price_data_for_tickers() ✓
    ├─ get_dividends() → Direct DB query (no repo wrapper) ✗
    └─ get_fundamentals() → Direct DB query (no repo wrapper) ✗

REPOSITORIES (DB Access)
    ├─ price_data.py
    │  ├─ get_price_data_daily() → Used by DataService ✓
    │  ├─ get_price_data_15_mins() → UNUSED ✗
    │  ├─ get_price_data_hourly() → UNUSED ✗
    │  ├─ fetch_bulk_price_data_for_tickers() → Used by DataService ✓
    │  └─ get_dividends_series() → Duplicated in DataService ✗
    │
    ├─ fundamental_data.py
    │  ├─ get_fundamental_data() → Tool wrapper + DataService wrapper ✗✗✗
    │  └─ HAS BUSINESS LOGIC (calculation fields) ✗
    │
    └─ Other repos ✓ (Simple query wrappers, mostly good)
```

---

## 6. CRITICAL HOTSPOTS

### Hotspot 1: `PortfolioConcentration` Class
**File:** `app/core/calculations/portfolio/concentration.py`

**Problems:**
- Lines 24-28: Direct DB coupling
- Lines 42-63: Uses `build_returns_df_for_dates()` (bypasses DataService)
- No simulation date support
- Tight coupling to Ticker model

**Impact:** Blocks backtesting, no caching, hard to test

### Hotspot 2: `build_returns_df_for_dates()` Helper
**File:** `app/core/calculations/core/helpers.py` (lines 323-360)

**Problems:**
- Calls repository functions directly (bypasses DataService/caching)
- No simulation date parameter
- Sequential dividend fetching (should be parallel)
- Used by critical VaR calculations

**Impact:** No caching, poor performance, blocks backtesting

### Hotspot 3: `fundamental_data.py` Repository
**File:** `app/repositories/fundamental_data.py`

**Problems:**
- Lines 105-108: Contains calculation logic (working_capital formula)
- Lines 26-200: Massive extraction logic (should be in service/tool layer)
- Wrapped by tool layer unnecessarily
- Wrapped by DataService unnecessarily

**Impact:** Business logic in data layer, over-engineered

### Hotspot 4: `fetch_repository_data()` Router
**File:** `app/core/agentic_framework/tool_lib/data_tools/repository.py`

**Problems:**
- 15+ branches (lines 51-104)
- Inconsistent return formats (some YAML, some dict)
- Performs date range calculations
- Acts as both router AND formatter

**Impact:** Hard to maintain, inconsistent behavior

---

## 7. RECOMMENDATION SUMMARY

### Immediate Actions (Violate no other principles)

1. **Remove unused functions:**
   - Delete `get_price_data_15_mins()`
   - Delete `get_price_data_hourly()`
   - Document that `fetch_bulk_price_data_for_tickers()` is the standard

2. **Move calculation logic out of repositories:**
   - Move `working_capital` calculation from `fundamental_data.py` to `PortfolioUtilities` or tool
   - Move `ohlc` resampling from `price_data.py` to calculations layer (not needed anyway)

3. **Unify simulation date handling:**
   - Rename all `end_date` in calculation classes to `_simulation_date`
   - Add `_simulation_date` support to `build_returns_df_for_dates()`

### Medium-term Refactoring (Architectural)

1. **Make DataService the ONLY path to data:**
   - Have `build_returns_df_for_dates()` use DataService (not direct repo)
   - Remove direct DB queries from `PortfolioConcentration`
   - Ensure all tools use DataService consistently

2. **Centralize dividend fetching:**
   - Either use `get_dividends_series()` OR `DataService.get_dividends()`, not both
   - Make dividend fetching parallel in helpers

3. **Remove unnecessary wrappers:**
   - Delete `ticker_fundamentals.py` tool wrapper (redundant)
   - Simplify `fundamental_data.py` repository (remove field extraction)

---

## 8. COMPLETE FUNCTION INVENTORY

### Price Data Access (5 functions, 3 unused/redundant)

| Function | File | Used | Frequency |
|----------|------|------|-----------|
| `get_price_data_15_mins()` | price_data.py | NO | 15-minute |
| `get_price_data_hourly()` | price_data.py | NO | Hourly (resampled) |
| `get_price_data_daily()` | price_data.py | YES | Daily (used by DataService) |
| `fetch_bulk_price_data_for_tickers()` | price_data.py | YES | Daily (bulk, parallel) |
| `fetch_bulk_ohlcv_data_for_tickers()` | price_data.py | MAYBE | Daily (full OHLCV) |

### Dividend Data Access (2 functions, 1 redundant)

| Function | File | Used | |
|----------|------|------|---|
| `get_dividends_series()` | price_data.py | YES | Direct access |
| `DataService.get_dividends()` | data_service.py | YES | Caching wrapper |

**Problem:** Both do same thing, `DataService` version not fully isolated

### Returns Calculation (3 function patterns, inconsistent)

| Function | File | Usage |
|----------|------|-------|
| `build_returns_df_for_dates()` | core/helpers.py | Portfolio concentration, VaR |
| `build_returns_df_from_price_map()` | core/helpers.py | Generic builder from price dict |
| `ReturnsCalculator.daily_price_returns()` | returns/calculator.py | Individual ticker returns |

### Fundamental Data Access (4-layer stack)

```
Tool (ticker_fundamentals.py)
  → Repository (fundamental_data.py:get_fundamental_data)
    → DataService (data_service.py:get_fundamentals)
      → Direct DB query
```

This is **unnecessarily deep**.

---

## 9. THE CLEAN ARCHITECTURE (What It Should Be)

```
┌─────────────────────────────────────────┐
│  TOOLS (Agent Interface)                │
│  - All tools use DataService ONLY       │
│  - No direct repository access          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  CALCULATIONS (Business Logic)          │
│  - Accept DataService via DI            │
│  - No DB coupling                        │
│  - Support _simulation_date everywhere  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  DATA SERVICE (Caching & Coordination)  │
│  - ONLY layer that calls repositories   │
│  - Manages in-memory caching            │
│  - Handles parallel fetching            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  REPOSITORIES (Pure Data Access)        │
│  - ONLY fetch from DB (no calculations) │
│  - Simple query wrappers                │
│  - No business logic                    │
└──────────────┬──────────────────────────┘
               │
           DATABASE
```

**Current state:** You have violations at every layer.

---

## 10. ARCHITECTURAL COMPLEXITY METRICS

| Metric | Count | Status |
|--------|-------|--------|
| **Price data fetch paths** | 4 | ❌ Should be 1 |
| **Unused repository functions** | 2 | ❌ Delete them |
| **Layers for fundamental data** | 4 | ❌ Should be 2 |
| **Direct DB queries in calculations** | 1+ | ❌ Should be 0 |
| **Functions bypassing DataService** | 2+ | ❌ Should be 0 |
| **Inconsistent simulation date APIs** | 3+ | ❌ Should be unified |

---

## CONCLUSION

The data fetching architecture has:

1. **DRY Violations:** 3-4 paths for same data, duplicate dividend logic, inconsistent patterns
2. **YAGNI Violations:** 2 unused price frequency functions, redundant tool wrappers
3. **KISS Violations:** 4-layer fundamental data stack, PortfolioConcentration DB coupling, inconsistent APIs
4. **Coupling:** DataService not universally used, direct DB queries in calculations layer
5. **Inconsistency:** Simulation date handling varies, return patterns differ, caching strategies mixed

### Impact on System

**Performance:** Duplicate fetching, no caching in critical paths
**Testability:** Direct DB coupling makes unit testing hard
**Backtesting:** Missing simulation date support blocks historical analysis
**Maintainability:** 4 different patterns for same task confuses developers

### Priority Refactoring Targets

1. **Fix PortfolioConcentration** (highest coupling violation)
2. **Fix build_returns_df_for_dates()** (blocks backtesting)
3. **Delete unused functions** (easy cleanup)
4. **Move calculations out of repositories** (abstraction leak)

The rest can wait, but these 4 are architectural violations that will cause issues.

---

**Recommended priority:** Fix `PortfolioConcentration` and `build_returns_df_for_dates()` hotspots first, then consolidate data fetching to use DataService exclusively.
