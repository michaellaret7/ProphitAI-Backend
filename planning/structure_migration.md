# Database Session Decorator Implementation Plan

## Overview
Implement decorators to eliminate repetitive database session management code across the codebase.

**Impact:** 56+ session creation instances across 26 files can be simplified.

## Decorators to Implement

### 1. @with_session decorator
- **Purpose:** Auto-manage database session lifecycle (create, provide, close)
- **Location:** `app/utils/decorators/database.py`
- **Session Types:** 'market', 'user', 'prophit'

### 2. @with_transaction decorator  
- **Purpose:** Handle transactions with automatic commit/rollback
- **Location:** `app/utils/decorators/database.py`
- **Use Cases:** Write operations that need commit/rollback logic

### 3. @with_sessions decorator (NEW)
- **Purpose:** Handle multiple database sessions in one function
- **Location:** `app/utils/decorators/database.py`
- **Use Cases:** Functions needing both UserSession and MarketSession
- **Example:** `add_portfolio`, `add_initial_positions`

## Files to Refactor

### High Priority - Repositories (20 functions)
These have the cleanest patterns and will show immediate benefit:

#### app/repositories/price_data.py (3 instances)
- [ ] `get_price_data_15_mins()` - MarketSession
- [ ] `get_price_data_daily()` - MarketSession with try-finally
- [ ] `get_dividends_series()` - MarketSession with try-finally

#### app/repositories/user_data.py (5 instances)
- [ ] `add_user()` - UserSession with commit
- [ ] `update_user_workos_id()` - UserSession with commit
- [ ] `add_company_user()` - UserSession
- [ ] `add_company()` - UserSession with commit
- [ ] `get_user_current_portfolio()` - UserSession

#### app/repositories/portfolio_data.py (6 instances)  
- [ ] `retrieve_portfolio()` - UserSession
- [ ] `add_portfolio()` - UserSession + MarketSession with commit
- [ ] `list_portfolios()` - UserSession
- [ ] `add_initial_positions()` - ProphitAltsSession + MarketSession

#### app/repositories/news_data.py (3 instances)
- [ ] `get_press_releases()` - MarketSession with try-finally
- [ ] `get_stock_news()` - MarketSession with try-finally
- [ ] `get_price_target_news()` - MarketSession with try-finally

#### app/repositories/ratings_data.py (5 instances)
- [ ] `get_stock_grades_individual()` - MarketSession
- [ ] `get_stock_grades_summary()` - MarketSession
- [ ] `get_ratings()` - MarketSession
- [ ] `get_analyst_recommendations()` - MarketSession
- [ ] `get_price_target_summary()` - MarketSession with try-finally

#### app/repositories/etf_data.py (2 instances)
- [ ] `get_etf_info()` - MarketSession with try-finally
- [ ] `get_etf_holdings()` - MarketSession with try-finally

#### app/repositories/transcripts_data.py (2 instances)
- [ ] `get_earnings_transcripts()` - MarketSession with try-finally
- [ ] `get_latest_transcript()` - MarketSession

#### app/repositories/prophit_alts_data.py (1 instance)
- [ ] `get_fund_final_positions()` - ProphitAltsSession with try-finally

### Medium Priority - Database Jobs (7 functions)
These have more complex patterns but would benefit:

#### app/db/jobs/fundamental_data.py (2 instances)
- [ ] `_update_single_ticker_fundamentals()` - Complex transaction handling
- [ ] Other methods with session management

#### app/db/jobs/ticker_table.py (3 instances)
- [ ] Functions with MarketSession and commit/rollback

#### app/db/jobs/price_table.py (2 instances)
- [ ] Functions with MarketSession and commit/rollback

#### app/db/core/add_etf.py (2 instances)
- [ ] `_load_dividends()` - MarketSession with rollback
- [ ] `load_etf_data()` - MarketSession with complex error handling

### Lower Priority - Other Files (29 instances)
These have varied patterns and may need custom handling:

#### app/domain/prophit_alts/consumer_staples_fund/build_portfolio/
- [ ] cio/tools.py (3 instances)
- [ ] cro/tools.py (1 instance)
- [ ] industry_agents/tools.py (2 instances)
- [ ] prompts/industry_prompts.py (1 instance)

#### app/core/calculations/
- [ ] core/data_service.py (2 instances)
- [ ] portfolio/concentration.py (1 instance)
- [ ] factors/momentum.py (1 instance)
- [ ] sectors/base.py (1 instance)

#### Other files
- [ ] app/utils/ticker_utils.py (2 instances)
- [ ] app/services/prophit_alts_service.py (2 instances)
- [ ] app/domain/stress_test/performance_analysis.py (1 instance)
- [ ] app/db/monitor/query_performance_check.py (1 instance)
- [ ] app/db/monitor/health_check.py (1 instance with rollback)
- [ ] app/db/core/build_price_table.py (1 instance)

## Implementation Steps

### Phase 1: Create Decorators (Day 1)
1. [x] Create `app/utils/decorators/database.py`
2. [x] Implement `@with_session` decorator
3. [x] Implement `@with_transaction` decorator
4. [x] Add unit tests for decorators

### Phase 2: Refactor Repositories (Day 2-3)
5. [x] Refactor price_data.py (test thoroughly)
6. [x] Refactor user_data.py
7. [x] Refactor portfolio_data.py (now uses with_sessions for multi-db)
8. [x] Refactor news_data.py
9. [x] Refactor ratings_data.py
10. [x] Refactor etf_data.py
11. [x] Refactor transcripts_data.py
12. [x] Refactor prophit_alts_data.py

### Phase 4: Refactor Remaining Files (Day 5)
17. [ ] Refactor calculation modules
18. [ ] Refactor prophit_alts modules
19. [ ] Refactor utility and service files

### Phase 5: Testing & Documentation (Day 6)
20. [ ] Run comprehensive test suite
21. [ ] Update documentation
22. [ ] Code review

## Benefits
- **Lines Removed:** ~280-350 lines of boilerplate code
- **Files Simplified:** 26 files
- **Functions Improved:** 56+ functions
- **Consistency:** Uniform session handling across codebase
- **Safety:** Guaranteed session cleanup and proper transaction handling
- **Maintainability:** Single point of control for session logic

## Notes
- Some functions use multiple sessions (e.g., MarketSession + UserSession) - these may need special handling
- Complex transaction patterns in db/jobs may require custom decorators
- Consider creating specialized decorators for common query patterns
