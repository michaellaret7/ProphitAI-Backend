# AGENTS.md

This file provides guidance to Codex when working with code in this repository.

## Overview

ProphitAI is an AI-powered institutional-grade portfolio management platform that uses a sophisticated agentic framework for portfolio optimization, analysis, and backtesting. The system leverages LLMs (OpenAI, Claude, Grok) to power autonomous agents that perform portfolio construction, risk analysis, and financial research.

## Development Environment

**Python Version:** 3.13.5
**Virtual Environment:** `.venv` (activate with `source .venv/bin/activate` on POSIX or `.\.venv\Scripts\Activate.ps1` in PowerShell) [Always activate venv before executing python commands]
**Package Manager:** UV (workspace-based monorepo)
**Workspace Config:** Root `pyproject.toml` defines UV workspace members
**Installing Packages:** Always use `uv sync` from the repo root — NEVER use `uv pip install -e`. On macOS, `uv pip install -e` creates `.pth` files that don't get processed correctly, causing `ModuleNotFoundError`. `uv sync` also resolves all workspace members together, preventing dependency version conflicts.

## Architecture

### Monorepo Structure

```
backend_restructure/
  packages/           # Reusable libraries (7 packages)
    shared/           # Foundational utilities (time, LLM client selection)
    atlas/            # Agentic framework (ReAct agents, tools, execution)
    data/             # Data layer (DB models, repositories, clients, jobs)
    calculations/     # Quantitative finance (risk, performance, factors, allocation)
    tools/            # Domain-specific agent tools (ticker, portfolio, broker, research)
    foundry/          # RAG system (ingestion, chunking, embeddings, retrieval)
    algo_trading/     # Algorithmic trading (strategies, backtesting, execution)
  projects/           # Deployable applications
    api/              # FastAPI REST/WebSocket API
  infra/              # Operational tooling
    jobs/             # Scheduled data jobs (EOD, EOW, intraday, screeners)
```

### Dependency Graph

```
API (prophitai-api)
  |-- Atlas (agents, execution)
  |-- Tools (all domain tools)
  |     |-- Calculations (quant math)
  |     |-- Data (repositories, clients)
  |     |-- Foundry (RAG search)
  |     +-- Shared (utilities)
  |-- Algo Trading (strategies, backtest)
  |-- Foundry (document RAG)
  +-- Shared (utilities)

Jobs (prophitai-jobs)
  |-- Data, Calculations, Shared
```

### Core Packages

#### 1. Atlas - Agentic Framework (`packages/atlas/src/prophitai_atlas/`)
The heart of ProphitAI - autonomous agent system for portfolio management:

- **Agents** (`agents/`):
  - `base.py`: `AgentBase` - abstract foundation for all agents
  - `agent.py`: `Agent` - general-purpose (max 200 iterations)
  - `planner_agent.py`: `PlannerAgent` - structured planning (5 iterations)
  - `worker_agent.py`: `WorkerAgent` - task execution from plans

- **Execution** (`execution/`):
  - `loop.py`: `ExecutionLoop` - ReAct loop until answer or max iterations
  - `tool_handler.py`: `ToolHandler` - tool invocation, validation, response handling
  - `validation.py`: Tool response validation
  - `utils.py`: String conversion, token counting

- **Tools** (`tools/`):
  - `decorator.py`: `@agent_tool` - auto-generates JSON Schema from type hints/docstrings
  - `catalogue.py`: `ToolCatalogue` - discovers and groups tools by category
  - `responses.py`: Tool response models
  - `base/`: Built-in tools (think, calculator, search_engine, update_plan, worker tools)

- **Models** (`models/`):
  - `callbacks.py`: `ChatCallback` protocol, `NoOpChatCallback`
  - `agent_response.py`: `AgentResponse` structured output
  - `chat.py`: `ChatSession` dataclass
  - `chat_events.py`: Streaming event types
  - `defaults.py`: Default LLM providers and models

- **Prompts** (`prompts/`): System prompts for planner, worker, and base agents
- **Logging** (`logging/`): `AgentPrinter` for pretty-printing agent thinking/tool use
- **Utils** (`utils/`): `gpt_parser.py` (JSON extraction from LLM), `token_count.py`

#### 2. Data Layer (`packages/data/src/prophitai_data/`)
Complete data access - DB models, repositories, clients, session management:

- **Database** (`db/`):
  - `config.py`: 4 SQLAlchemy engines (market_data, user_data, prophit_alts, macro_data)
  - `models/`: `market.py`, `user.py`, `alts.py`, `macro.py`

- **Session Management** (`session/decorators.py`) - CRITICAL:
  - `@with_session(session_type='market')` - creates/closes session automatically
  - `@with_transaction(session_type='user')` - wraps in commit/rollback
  - `@with_sessions(user_session='user', market_session='market')` - multiple sessions
  - Session types: `'market'`, `'user'`, `'prophit'`, `'macro'`

- **Repositories** (`repositories/`):
  - `price.py`, `ticker.py`, `etf.py`, `news.py`, `ratings.py`, `screener.py`, `transcripts.py`
  - `fundamentals/`: Financial statements, fetchers
  - `macro/`: Rates, commodities, indicators, calendar
  - `portfolio/`: CRUD, retrieval, alerts, preferences
  - `messaging/`: Conversations, messages, read state
  - `user/`: Account, trade proposals, watchlist

- **Clients** (`clients/`):
  - `fmp.py`: Financial Modeling Prep API
  - `snaptrade/`: Brokerage integration (accounts, auth, trading, models)
  - `options/`: Options data (client, repository, service)

- **Jobs** (`jobs/`): Market price updates, fundamentals, macro data, portfolio monitoring
- **Cache** (`cache/`): `data_cache.py` - caching layer

#### 3. Calculations (`packages/calculations/src/prophitai_calculations/`)
Quantitative finance calculations:

- `factors/`: Value, Growth, Momentum, Quality, Size, Volatility
- `performance/`: Returns, Sharpe, Sortino, Calmar, Information Ratio
- `risk/`: Volatility, VaR, Expected Shortfall, Drawdown, Benchmark comparison
- `stress_test/`: Multi-scenario stress testing
- `technicals/`: Momentum, trend, volatility, volume, statistical indicators
- `portfolio_allocator/`: Portfolio optimization (Mean-Variance, HRP, etc.)
- `portfolio_analytics/`: Correlation, covariance, factor exposures, group metrics
- `models/`: Pydantic result models for all calculation types

#### 4. Tools (`packages/tools/src/prophitai_tools/`)
Domain-specific agent tools - all use `@agent_tool(category="...")` decorator:

- `registry.py`: Central registry - imports all tool functions, exports `ALL_TOOL_FUNCTIONS`
- `ticker/`: Performance, risk, factors, technicals, fundamentals, info
- `portfolio/`: Performance, risk, stress test, factor exposure, correlation, allocator
- `broker/`: Account info, positions, trade proposals, orders, options trades
- `options/`: Expirations, contracts, chains, quotes, price history
- `research/`: Macro, earnings calls, credit, economics, user uploads, tax, theory (RAG-powered)
- `macro/`: Commodity prices, indicators, US rates
- `news/`: General news, ticker news, press releases
- `screener/`: Equity and ETF screening
- `watchlist/`: Watchlist retrieval

#### 5. Foundry - RAG System (`packages/foundry/src/prophitai_foundry/`)
Document ingestion, chunking, embedding, and retrieval:

- `ingestion/`: PDF, text, Excel document loaders (Modal serverless for PDF extraction)
- `chunking/`: Recursive, semantic, and earnings-call-specific chunking
- `embeddings/`: Voyage AI embeddings stored in Pinecone vector DB
- `retrieval/`: Vector search, hybrid search, query decomposition, reranking
- `models/`: Document, chunk, vector, metadata models

#### 6. Algo Trading (`packages/algo_trading/src/prophitai_algo_trading/`)
Algorithmic trading strategies and backtesting:

- `strategies/`: 7 strategies (Ichimoku, Kalman StatArb, MACD, ORB, RSI, Squeeze, VWAP-Hurst)
- `engines/`: Event-driven and vectorized backtesting, live trading
- `execution/`: Cost model, position sizing, portfolio tracking
- `indicators/`: Technical indicator implementations
- `broker/`: Alpaca integration
- `data/`: Market data clients (Alpaca, FMP, Yahoo Finance)

#### 7. Shared (`packages/shared/src/prophitai_shared/`)
Foundational utilities used by all packages:

- `time_utils.py`: UTC time management (CRITICAL - see Timezone section)
- `choose_model_and_client.py`: LLM provider abstraction (`get_model_and_client()`)

### API Project (`projects/api/src/prophitai_api/`)
FastAPI REST/WebSocket API - main backend service:

- **Entry Point**: `projects/api/main.py` (Uvicorn)
- **App Factory**: `app.py` (lifespan, middleware, CORS, GZip)

- **Routes** (`routes/`): 25+ route modules
  - agent, broker, cache, chat, crypto, dashboard, document, etf, fundamentals, macro, messaging, news, portfolio, price, screener, search, technical, ticker, trade_proposal, user, watchlist, webhook, websocket

- **Controllers** (`controllers/`): Business logic layer
  - `broker/`: Account, connections, trading
  - `portfolio/`: Analytics, operations
  - `watchlist/`: CRUD, operations
  - `foundry/`: Document processing with S3/pipeline helpers
  - `fundamentals/`, `macro/`, plus standalone controllers

- **Services** (`services/`): Business logic implementation
  - `broker/`: Account, connections, trading, proposals, onboarding
  - `portfolio/`: Metrics, returns, factors, concentration, stress, comparison
  - `shared/`: `chat_executor.py` (session management), `agent_executor.py`, `connection_manager.py` (WebSocket), `pdf_service.py`
  - `crypto/`, `etfs/`, `macro/`, `search/`, `technical/`, `messaging/`

- **Agents** (`agents/`): Domain agents (clarify, portfolio_builder, watchlist)
- **Auth** (`auth/`): API key validation, Clerk authentication
- **Cache** (`cache/`): Redis client
- **Schemas** (`schemas/`): Request/response Pydantic models

### Infrastructure (`infra/jobs/src/prophitai_jobs/`)
Scheduled data jobs with CLI entry points:

- `runs/`: `eod.py`, `eow.py`, `intraday.py`, `screeners.py`, `run_all.py`
- `screeners/`: Equity and ETF screener implementations
- `monitor/`: Health checks, query performance monitoring
- CLI commands: `prophitai-run-eod`, `prophitai-run-eow`, `prophitai-run-intraday`, `prophitai-run-screeners`, `prophitai-run-all`

## Key Design Patterns

### Agent Execution Flow
1. Agent receives message + tools via `Agent(tools=...)`
2. `ExecutionLoop` starts ReAct iteration
3. LLM called with tool schemas via `client.chat.completions.create()`
4. `ToolHandler` processes tool calls, validates responses
5. Results appended to messages, loop continues until text-only response or max iterations

### Tool Registration Pattern
1. Define function with `@agent_tool(category="category_name")` decorator
2. Import in `packages/tools/src/prophitai_tools/registry.py`
3. `ToolCatalogue` auto-discovers and groups tools by category
4. Inject into Agent via `Agent(tools=ALL_TOOL_FUNCTIONS)`

### API Layering (Clean Architecture)
```
Routes (FastAPI endpoints)
  --> Controllers (request handling, orchestration)
    --> Services (business logic)
      --> Repositories/Clients (data access)
        --> Database/External APIs
```

### Session Management
```python
@with_session(session_type='market')        # Single session
@with_transaction(session_type='user')      # With commit/rollback
@with_sessions(user_session='user', market_session='market')  # Multiple
```

### Callback Pattern for Streaming
- `ChatCallback` protocol defines interface (in `atlas/models/callbacks.py`)
- `WebSocketChatCallback` implements streaming to clients
- `NoOpChatCallback` for non-streaming execution

## Database Architecture

4 separate PostgreSQL databases, each with its own SQLAlchemy engine:

| Database | Session Type | Pool Size | Purpose |
|----------|-------------|-----------|---------|
| `market_data` | `'market'` | 40 | Ticker, price, ETF, fundamentals, news |
| `user_data` | `'user'` | 10 | User accounts, watchlists, portfolios |
| `prophit_alts` | `'prophit'` | 10 | Alternative investment data |
| `macro_data` | `'macro'` | 10 | Economic indicators, rates, commodities |

**Config**: `packages/data/src/prophitai_data/db/config.py`
**Models**: `packages/data/src/prophitai_data/db/models/`

## Development Guidelines

### Timezone Handling (CRITICAL)
**All datetime operations MUST use UTC time to ensure data consistency**

- **NEVER use `datetime.now()`** - This returns server local time and causes timezone misalignment
- **ALWAYS use `get_current_utc_time()`** from `prophitai_shared` for current time
- **Database stores UTC timestamps as naive datetimes** - All times are in UTC without timezone info
- **Price data from FMP API arrives in EST** - Converted to UTC before storage

#### Required Import
```python
from prophitai_shared import get_current_utc_time, get_utc_date_str, get_utc_days_ago
```

#### Available Functions
- `get_current_utc_time()` - Returns current UTC time as naive datetime
- `get_utc_date_str()` - Returns current UTC date as 'YYYY-MM-DD' string
- `get_utc_days_ago(days)` - Returns UTC time N days ago
- `get_utc_date_range(lookback_days)` - Returns (start_date, end_date) tuple
- `ensure_naive_utc(dt)` - Ensures naive UTC datetime
- `get_utc_timestamp_str()` - Returns UTC timestamp as string

#### Why This Matters
- Server runs in EST (4 hours behind UTC)
- Database stores all timestamps in UTC
- Using local time causes 4-hour data misalignment
- Results in incorrect calculations, missing recent data, and wrong backtesting results

### Core Development Philosophy
**KISS (Keep It Simple, Stupid)**
- Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

**YAGNI (You Aren't Gonna Need It)**
- Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

**DRY (Don't Repeat Yourself)**
- Keep every piece of knowledge in a single, authoritative place. Duplicate code/config/business rules drift out of sync and create bugs. Extract shared logic into reusable functions/modules, reuse components whenever possible, and rely on single sources of truth.
   --> To avoid repetition: use decorators where appropriate, search the codebase for existing functions or classes before writing new ones, and focus on building reusable, readable abstractions.

**Design Principles**
- Dependency Inversion: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- Open/Closed Principle: Software entities should be open for extension but closed for modification.
- Single Responsibility: Each function, class, and module should have one clear purpose.
- Fail Fast: Check for potential errors early and raise exceptions immediately when issues occur.

**Development Goals**
- Scalable Architecture: Build stateless services where possible; pass state as arguments rather than relying on local server memory to ensure horizontal scaling.
- Modular OOP: Use Classes to encapsulate logic, but maintain a strict Separation of Concerns between data processing and I/O.
- DRY & Reuse: Check helpers or utils before coding. Refactor shared logic into pure, reusable functions to minimize duplication.
- Type Safety: Mandate Type Hints and explicit return types to ensure the codebase remains self-documenting and maintainable.
- Resource Efficiency: Use Context Managers for all I/O and prioritize vectorized operations for data-heavy tasks.

**Rules**
- When a function or class takes a portfolio as a parameter it should always be tickers: List[str] and weights: List[float] (decimal percentages, e.g. 0.30 = 30%)

### Code Documentation
- Every module should have a docstring explaining its purpose
- Public functions must have complete docstrings
- Complex logic should have inline comments with # Reason: prefix
- Keep README.md updated with setup instructions and examples
- Maintain CHANGELOG.md for version history

### Code Constraints
- **Files**: Max 500 lines - split into modules if approaching limit
- **Functions**: Max 50 lines with single responsibility
- **Classes**: Max 100 lines representing single concept
- **Organization**: Organize code into clearly separated modules, grouped by feature or responsibility

### Naming Conventions
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private attributes: `_leading_underscore`
- Type aliases/Enums: `PascalCase` / `UPPER_SNAKE_CASE`

### Documentation Requirements
- Module docstrings explaining purpose
- Complete docstrings for public functions
- Inline comments with `# Reason:` prefix for complex logic

### Complexity Gauging
- Before executing any task, assess its complexity to ensure your approach is optimally engineered.
- Evaluate whether the proposed approach is under-engineered, optimally engineered, or over-engineered.

## Branching Strategy

- `main`: Production-ready code
- `dev`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation
- `refactor/*`: Code refactoring
- `test/*`: Test additions/fixes

## Commenting Strategy and Helper functions
- Always put helper functions at the top of the file
- Always comment them in blocks like such
        ================================
    --> Helper funcs
        ================================

## External Dependencies

### Core
- **FastAPI**: Web framework and API - https://fastapi.tiangolo.com/
- **Pydantic**: Data validation and settings - https://docs.pydantic.dev/
- **SQLAlchemy**: ORM and database access
- **PostgreSQL**: 4 databases (market, user, alts, macro)
- **Redis**: Caching layer

### AI/ML
- **OpenAI/Claude/Grok**: LLM providers for agents
- **Pinecone**: Vector database for RAG
- **Voyage AI**: Embedding model
- **Langfuse**: LLM observability/tracing

### Finance
- **FMP (Financial Modeling Prep)**: Market data API
- **Snaptrade**: Brokerage integration
- **Alpaca**: Trading and market data
- **PyPortfolioOpt/CVXPY**: Portfolio optimization

### Data
- **Pandas/NumPy/SciPy**: Data analysis and numerical computation

## Important Files

- `projects/api/main.py`: FastAPI application entrypoint
- `projects/api/src/prophitai_api/app.py`: FastAPI factory (lifespan, middleware)
- `packages/atlas/src/prophitai_atlas/agents/agent.py`: Core Agent class
- `packages/atlas/src/prophitai_atlas/execution/loop.py`: ReAct execution loop
- `packages/atlas/src/prophitai_atlas/tools/decorator.py`: `@agent_tool` decorator
- `packages/tools/src/prophitai_tools/registry.py`: Tool registry (all tool imports)
- `packages/data/src/prophitai_data/db/config.py`: Database engine configuration
- `packages/data/src/prophitai_data/session/decorators.py`: Session management decorators
- `packages/shared/src/prophitai_shared/time_utils.py`: UTC time utilities
- `packages/shared/src/prophitai_shared/choose_model_and_client.py`: LLM provider selection
- `projects/api/src/prophitai_api/services/shared/chat_executor.py`: Chat session management
- `.env`: Environment variables (API keys, DB credentials) - **NEVER COMMIT**
- `pyproject.toml`: UV workspace configuration

## Important Rules

- Never create a README.md for a specific functionality unless specifically requested
- Do not create an excess of test files — create and fix one, not duplicates
- Do not hesitate to correct the user if something is wrong. The most important thing is being correct and writing effective code
- Always use the fetch_bulk_price_data_for_tickers function for stock price fetching unless told otherwise
- Never create **Backwards Compatibility** — build the new solution and change everything it affects
- Do not create code functionality that requires arg commands to run (e.g., `tests/hrp_comb.py --mode long-only`)
- Never name a folder or file with a '_' in front
- Anytime you want to record a spec, standard, pattern, or anything you might need to reference later, write a document about it in `docs/`. Organize by topic (e.g., `docs/tools/`, `docs/agents/`)

## Testing
1. Do not use pytest fixtures or mocks
2. Create REAL TESTS WITH REAL DATA
3. For example to test the allocator: get real data from repositories, inject it into the allocate function, grade on output and functionality
4. Same for agent tests — keep it simple, keep it real
