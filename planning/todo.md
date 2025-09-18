# Stock Screener Development Plan (High-Level)

## Overview
Build a fast, efficient stock screener tailored to our Postgres schemas and existing data-access utilities. Keep the API simple, use tuple-based filters, and JOIN only what’s needed. No caching anywhere in the screener.

## Database Architecture Map (from app/db/core/schema.json)
- Market_data
  - ticker_universe.tickers: id, ticker, sector, industry, sub_industry, is_etf, price, market_cap, avg_volume, eps, pe, dollar_volume, last_updated
  - fundamental_data.* (keyed by ticker_id): balance_sheets, cash_flow_statements, income_statements, financial_ratios, analyst_estimates, etf_holdings, etf_info, dividends, earnings_transcript, fundamental_reports
  - price_data.prices: (ticker_id, datetime, open, high, low, close, volume)
  - news_data.*: press_releases, stock_news, price_target_news, stock_grade_news
  - grades_and_ratings_data.*: stock_grades_individual, stock_grades_summary, rating_scores, analyst_recommendations, price_target_summary
- User_data: users, companies, company_users, portfolios
- prophit_alts: prophit_alts_funds.* (funds, trades, initial_positions, final_positions)

Key relationships
- All Market_data child tables reference `ticker_universe.tickers.id` via `ticker_id`.
- Time-series tables access by `(ticker_id, date|datetime)`; latest-row snapshots are common.

## Relevant Code Map (DB + Access Layer)
- app/db/core/db_config.py: engines + sessions (MarketSession, UserSession, ProphitAltsSession)
- app/db/core/market_data_models.py: ORM models for Market_data schemas
- app/db/core/user_data_models.py, app/db/core/prophit_alts_models.py
- app/utils/decorators/database.py: `with_session`, `with_transaction`
- app/core/calculations/core/data_service.py: read helpers (note: the screener will NOT use caching)
- app/repositories/
  - price_data.py, fundamental_data.py, ratings_data.py, news_data.py, transcripts_data.py, portfolio_data.py

## Screener Scope
- Primary table: `ticker_universe.tickers`
- Optional joins (on demand): latest `fundamental_data.financial_ratios`, latest `price_data.prices`, `fundamental_data.etf_info`, selected `grades_and_ratings_data` tables
- Output: pandas DataFrame (optionally JSON). Supports limit, offset, column selection, and multi-column sort.
- Coverage: expose ALL available fundamental and technical data points present in schemas and calculations (ratios, margins, liquidity, turnover, valuation, prices/technicals, ETF fields, analyst/ratings, etc.).

## Filter API (tuple-based)
- Numeric: (min, max) => BETWEEN; (min, None) => >=; (None, max) => <=
- List => IN
- String/Bool => exact match
- Examples: `pe_ratio=(5,20)`, `market_cap=(1e9,None)`, `sector="Technology"`, `industry=["Software","Hardware"]`, `is_etf=False`

## Performance & Indexing (research-backed)
- Push predicates to SQL only; select only requested columns
- Composite/covering indexes on frequent filters/sorts: `(ticker)`, `(sector,industry)`, `(market_cap)`, `(pe)`, `(dollar_volume)`, `(ticker_id,date DESC)`
- Latest-snapshot subqueries or materialized view for “latest fundamentals per ticker”
- Parallel fetching avoided in SQL path; use a single optimized query per screen
Note: No caching. All queries are executed against the database; freshness prioritized.

## Implementation Plan
1) Core Screener (repositories/screener.py)
- StockScreener.screen(limit=100, offset=0, sort_by=None, columns=None, **filters)
- Build dynamic FROM/WHERE based on filters and requested columns
- Lazy JOIN only needed tables; use latest-row subqueries for time-series
- Parameterized SQL (no string interpolation)

2) Validation & Models
- Add simple input validation (allowed columns, types, ranges)
- Optional: lightweight models under app/models if needed later (no file creation now)

3) Performance
- Verify key indexes exist (see list above)
Note: No caching will be implemented in the screener.

4) Sorting & Output
- Support multi-column sort (`-col` for DESC)
- Column whitelist and projection
- Return DataFrame; helper to JSON serialize

5) Integration
- Use `MarketSession` and `with_session` decorator
- Reuse `DataService` selectively for query building patterns only (not caching)
- Add minimal tests under `tests/` later (when approved)

## Notes on Workflow
- Follow internal workflow_instructions.mdc structure: discovery → design → implement → test → integrate. Pausing implementation after planning per request.

## Status
- Discovery completed (DB structure reviewed, access patterns identified)
- Web research incorporated (indexing, snapshots, dynamic query building, no caching)
- Awaiting approval to implement
