# ProphitAI Monorepo

A uv workspace monorepo for the ProphitAI platform — an AI-powered institutional-grade portfolio management system. This repo consolidates all backend systems (agent framework, quantitative finance, data layer, algorithmic trading, RAG, and API) into a single repository with clear package boundaries and explicit dependencies.

## Architecture

The monorepo is organized into **7 packages** (reusable libraries), **1 project** (deployable application), and **1 infra job runner**. The design is modeled after Apache Airflow's approach: a core framework consumed by multiple packages, all managed with uv workspaces and a single lockfile.

### Dependency Graph

```
                ┌──────────┐
                │  shared   │
                └─────┬─────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
┌─────▼─────┐  ┌─────▼─────┐  ┌──────▼─────┐
│   atlas   │  │   calc    │  │    data    │
│(framework)│  │ (calcs)   │  │ (db/repos) │
└─────┬─────┘  └─────┬─────┘  └──────┬─────┘
      │               │               │
      └───────┬───────┴───────────────┘
              │
       ┌──────▼──────┐    ┌────────────────┐    ┌──────────┐
       │    tools    │    │  algo_trading   │    │ foundry  │
       │(agent tools)│    │   (trading)     │    │  (RAG)   │
       └──────┬──────┘    └────────┬───────┘    └────┬─────┘
              │                    │                  │
              └────────┬───────────┴──────────────────┘
                       │
                  ┌────▼───┐       ┌────────┐
                  │  api   │       │  jobs  │
                  │        │       │(infra) │
                  │+redis  │       └────────┘
                  └────────┘
```

Key architectural decisions:

- **`algo_trading` and `tools` are independent branches.** Algo is pure trading machinery with no knowledge of agents or AI. Tools is the agent composition layer that wires atlas + calculations + data together.
- **`atlas` has zero domain dependencies.** It depends only on `shared`, making it publishable to PyPI as a standalone agent framework.
- **`api` is where everything converges.** It imports tools for agent capabilities, foundry for RAG, and algo_trading for trading — but none of those packages know about each other.
- **`jobs` is the data pipeline runner.** It depends on data, calculations, and shared — no agent or API dependencies.

## Repo Structure

```
backend_restructure/
├── pyproject.toml                    # uv workspace definition
├── uv.lock                           # Single lockfile for all packages
├── Makefile                          # Dev targets (sync, dev, test, lint, format)
├── .python-version                   # 3.13.5
├── pyrightconfig.json
├── .claude/
│
├── packages/
│   ├── shared/                       # Minimal shared utilities
│   │   ├── pyproject.toml            # "prophitai-shared"
│   │   └── src/
│   │       └── prophitai_shared/
│   │           ├── time_utils.py     # get_current_utc_time() — universal
│   │           └── choose_model_and_client.py  # LLM provider abstraction
│   │
│   ├── atlas/                        # PURE agent framework (no domain dependencies)
│   │   ├── pyproject.toml            # "prophitai-atlas"
│   │   └── src/
│   │       └── prophitai_atlas/
│   │           ├── agents/           # Base agent, planner, worker
│   │           ├── execution/        # ReAct loop, tool handler, validation
│   │           ├── tools/            # Framework primitives
│   │           │   ├── decorator.py  # @agent_tool decorator
│   │           │   ├── catalogue.py  # Tool discovery and grouping
│   │           │   ├── responses.py  # Tool response models
│   │           │   └── base/         # think, calculator, search_engine, update_plan, worker
│   │           ├── models/           # Agent response, callbacks, chat, events, defaults
│   │           ├── prompts/          # base, planner, worker, plan_injection
│   │           ├── evaluation/       # Agent evaluation
│   │           ├── gym/              # Agent training/testing
│   │           ├── logging/          # Agent printer
│   │           └── utils/            # gpt_parser, token_count
│   │
│   ├── calculations/                 # Quantitative finance calculations (pure math)
│   │   ├── pyproject.toml            # "prophitai-calculations"
│   │   └── src/
│   │       └── prophitai_calculations/
│   │           ├── factors/          # Value, Growth, Momentum, Quality, Size, Volatility
│   │           ├── performance/      # Returns, ratios (Sharpe, Sortino, etc.)
│   │           ├── risk/             # VaR, drawdown, benchmark comparison
│   │           ├── stress_test/      # Multi-scenario stress testing
│   │           ├── technicals/       # Momentum, trend, volatility, volume, statistical
│   │           ├── portfolio_allocator/  # Mean-Variance, HRP, constraints, strategies
│   │           ├── portfolio_analytics/  # Correlation, covariance, factor exposures, groups
│   │           └── models/           # Pydantic result models for all calculation types
│   │
│   ├── data/                         # Data layer (DB, repos, clients, jobs, caching)
│   │   ├── pyproject.toml            # "prophitai-data"
│   │   └── src/
│   │       └── prophitai_data/
│   │           ├── db/               # 4 SQLAlchemy engines, models (market, user, alts, macro)
│   │           ├── session/          # @with_session, @with_transaction, @with_sessions decorators
│   │           ├── repositories/     # Data access layer
│   │           │   ├── price.py, ticker.py, etf.py, news.py, ratings.py, screener.py, transcripts.py
│   │           │   ├── alts/
│   │           │   ├── fundamentals/ # Fetchers, statements, models
│   │           │   ├── macro/        # Rates, commodities, indicators, calendar
│   │           │   ├── messaging/    # Conversations, messages, read state
│   │           │   ├── portfolio/    # CRUD, retrieval, alerts, preferences
│   │           │   └── user/         # Account, trade proposals, watchlist
│   │           ├── clients/          # FMP, SnapTrade, options
│   │           ├── jobs/             # Market, fundamentals, macro, portfolio monitoring
│   │           ├── cache/            # DataCache — in-memory OHLCV/fundamentals cache
│   │           └── internal/         # Encryption utilities
│   │
│   ├── tools/                        # Shared agent tool library (composition layer)
│   │   ├── pyproject.toml            # "prophitai-tools"
│   │   └── src/
│   │       └── prophitai_tools/
│   │           ├── registry.py       # Central registry — imports all tools, exports ALL_TOOL_FUNCTIONS
│   │           ├── ticker/           # Performance, risk, factors, technicals, fundamentals, info
│   │           ├── portfolio/        # Performance, risk, stress test, correlation, allocator
│   │           ├── broker/           # Account, positions, trades, orders, options trades
│   │           ├── options/          # Expirations, contracts, chains, quotes, price history
│   │           ├── research/         # Macro, earnings calls, credit, economics, tax, theory, uploads
│   │           ├── screener/         # Equity and ETF screening
│   │           ├── macro/            # Commodity prices, indicators, US rates
│   │           ├── news/             # General news, ticker news, press releases
│   │           └── watchlist/        # Watchlist retrieval
│   │
│   ├── foundry/                      # RAG system (embeddings, chunking, retrieval)
│   │   ├── pyproject.toml            # "prophitai-foundry"
│   │   └── src/
│   │       └── prophitai_foundry/
│   │           ├── ingestion/        # PDF, text, Excel loaders (Modal serverless for PDF)
│   │           ├── chunking/         # Recursive, semantic, earnings-call-specific
│   │           ├── embeddings/       # Voyage AI embeddings, Pinecone vector DB, sparse encoder
│   │           ├── retrieval/        # Vector/hybrid search, reranking, query decomposition
│   │           ├── models/           # Document, chunk, vector, metadata models
│   │           ├── pipeline.py       # Ingestion pipeline orchestration
│   │           └── utils/
│   │
│   └── algo_trading/                 # Algorithmic trading LIBRARY (pure machinery)
│       ├── pyproject.toml            # "prophitai-algo_trading"
│       └── src/
│           └── prophitai_algo_trading/
│               ├── strategies/       # BaseStrategy + 7 concrete strategies
│               │   ├── base.py
│               │   ├── macd_momentum/
│               │   ├── rsi_mean_reversion/
│               │   ├── ichimoku_cross/
│               │   ├── orb_breakout/
│               │   ├── squeeze_breakout/
│               │   ├── vwap_hurst_btc/
│               │   └── kalman_stat_arb/
│               ├── indicators/       # Pure technical indicator calculators
│               ├── engines/          # Execution engines
│               │   ├── live.py       # LiveRunner (ZMQ subscriber)
│               │   ├── trade_routing.py
│               │   └── backtest/     # Vectorized + event-driven backtesting
│               ├── execution/        # Portfolio/position management, cost model
│               ├── broker/           # Alpaca interface
│               ├── data/             # Data clients (Alpaca, FMP, yfinance), DB, streaming
│               └── utils/
│
├── projects/
│   └── api/                          # ProphitAI API service
│       ├── pyproject.toml            # "prophitai-api"
│       ├── main.py                   # Uvicorn entrypoint
│       └── src/
│           └── prophitai_api/
│               ├── app.py            # FastAPI factory (lifespan, middleware, CORS)
│               ├── routes/           # 24 route modules
│               ├── controllers/      # Request handling, orchestration
│               │   ├── broker/       # Account, connections, trading
│               │   ├── portfolio/    # Analytics, operations
│               │   ├── watchlist/    # CRUD, operations
│               │   ├── foundry/      # Document processing with S3/pipeline
│               │   ├── fundamentals/ # Company, estimates, ratings
│               │   └── macro/        # Economic, market, sector
│               ├── services/         # Business logic
│               │   ├── broker/       # Account, connections, trading, proposals, onboarding
│               │   ├── portfolio/    # Metrics, returns, factors, stress, comparison
│               │   ├── shared/       # chat_executor, agent_executor, connection_manager, pdf
│               │   └── ...           # crypto, etfs, macro, messaging, search, technical
│               ├── agents/           # Domain agents (clarify, portfolio_builder, watchlist)
│               │   └── prompts/      # Agent-specific prompts
│               ├── auth/             # Clerk JWT, API key validation
│               ├── cache/            # Redis client
│               ├── schemas/          # Request/response Pydantic models
│               └── utils/            # Case conversion, decorators, validation, serialization
│
└── infra/
    └── jobs/                         # Scheduled data jobs
        ├── pyproject.toml            # "prophitai-jobs"
        └── src/
            └── prophitai_jobs/
                ├── runs/             # eod, eow, intraday, screeners, run_all
                ├── screeners/        # Equity and ETF screener implementations
                ├── monitor/          # Health checks, query performance
                └── utils/            # Timezone fixes, transcript fixes
```

## Packages

| Package | PyPI Name | Description | Key Dependencies |
|---------|-----------|-------------|------------------|
| `packages/shared` | `prophitai-shared` | Minimal shared utilities (time, LLM client selection) | `pydantic` |
| `packages/atlas` | `prophitai-atlas` | Pure agent framework — ReAct loop, tool registry, evaluation | `shared`, `openai`, `tiktoken` |
| `packages/calculations` | `prophitai-calculations` | Quantitative finance — risk, factors, portfolio analytics, technicals | `shared`, `pandas`, `numpy`, `scipy` |
| `packages/data` | `prophitai-data` | Data layer — DB models, repositories, jobs, external API clients, caching | `shared`, `sqlalchemy`, `pandas` |
| `packages/tools` | `prophitai-tools` | Agent tool library — composes atlas + calculations + data into callable tools | `atlas`, `calculations`, `data`, `shared` |
| `packages/foundry` | `prophitai-foundry` | RAG system — embeddings, chunking, ingestion, retrieval | `shared`, `openai`, `pinecone`, `voyageai` |
| `packages/algo_trading` | `prophitai-algo_trading` | Algorithmic trading — strategies, engines, indicators, execution, broker | `shared`, `pandas`, `numpy`, `alpaca-py`, `pyzmq` |

| Deployable | PyPI Name | Description | Key Dependencies |
|------------|-----------|-------------|------------------|
| `projects/api` | `prophitai-api` | FastAPI application — routes, controllers, auth, Redis caching | `tools`, `foundry`, `algo_trading`, `atlas`, `data`, `calculations`, `shared`, `fastapi`, `redis` |
| `infra/jobs` | `prophitai-jobs` | Scheduled data jobs — EOD, EOW, intraday, screeners, monitoring | `data`, `calculations`, `shared` |

## Naming Convention

All importable Python packages use the `prophitai_` prefix:

```python
from prophitai_atlas.agents import AgentBase
from prophitai_calculations.risk import calculate_var
from prophitai_algo_trading.strategies.macd_momentum import MACDMomentum
from prophitai_algo_trading.engines import LiveRunner, VectorizedBacktestEngine
```

Why `prophitai_*` over short names:

- **Collision safety** — `data`, `shared`, `tools` are generic and will collide with third-party packages
- **Grep-ability** — `from prophitai_atlas.agents import ...` is immediately identifiable as project code
- **PyPI publishability** — `prophitai-atlas` is unambiguous on PyPI
- **Consistency** — no cognitive overhead deciding which packages are prefixed

## Setup

```bash
# Clone and sync
git clone https://github.com/Prophit-AI/backend_restructure.git
cd backend_restructure

# Install all workspace packages in editable mode
uv sync

# Copy .env.example and fill in your keys
cp .env.example .env
```

## Development

```bash
# Run the API server
make dev

# Run all tests
make test

# Lint and format
make lint
make format

# Type checking
make typecheck

# Clean caches
make clean

# Run a specific package's tests
uv run pytest packages/algo_trading/tests/
```

## CLI Commands (Jobs)

```bash
# Run end-of-day data sync
prophitai-run-eod

# Run end-of-week data sync
prophitai-run-eow

# Run intraday data sync
prophitai-run-intraday

# Run screeners
prophitai-run-screeners

# Run all jobs
prophitai-run-all
```
