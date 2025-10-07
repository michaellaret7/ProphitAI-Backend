# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ProphitAI is an AI-powered institutional-grade portfolio management platform that uses a sophisticated agentic framework for portfolio optimization, analysis, and backtesting. The system leverages LLMs (OpenAI, Claude, Grok) to power autonomous agents that perform portfolio construction, risk analysis, and financial research.

## Development Environment

**Python Version:** 3.13.5
**Virtual Environment:** `.venv` (activate with `source .venv/bin/activate`) [Always activate venv before executing python commands]
**Package Manager:** pip

## Architecture

### Core Components

#### 1. Agentic Framework (`app/core/agentic_framework/`)
The heart of ProphitAI - a sophisticated autonomous agent system for portfolio management:

- **BaseAgent** (`base_agent/agent.py`): Foundation for all specialized agents
  - Implements ReAct pattern with native tool-calling
  - Manages conversation history and token accounting
  - Handles iteration limits and stagnation detection
  - Supports multiple LLM providers (OpenAI, Claude, Grok)

- **Task Management System** (`base_agent/tasks/`):
  - `manager.py`: TodoList with MainTask/SubTask hierarchy
  - `execution_engine.py`: PlanExecutionEngine for executing task plans
  - `models.py`: Pydantic models (TodoList, MainTask, SubTask, TaskStatus)
  - `validator.py`: Task validation logic

- **Memory Systems** (`base_agent/memory/`):
  - `domain_memory.py`: Agent-specific knowledge (CIO portfolio construction patterns)
  - `episodic_memory.py`: Recent successful tool executions for learning

- **Tool Library** (`tool_lib/`):
  - `data_tools/`: Market data, fundamentals, stock screening
  - `risk_tools/`: Covariance, VaR/ES, stress testing, drawdowns
  - `portfolio_tools/`: Portfolio metrics, concentration, beta
  - `ticker_tools/`: Ticker-specific analysis, performance, factors
  - `agent_specific_tools/`: Specialized tools for CIO, CRO, Industry agents

#### 2. Domain-Specific Agents (`app/domain/`)
Specialized agents for different investment strategies:

- **ProphitAlts** (`prophit_alts/consumer_staples_fund/`):
  - CIO Agent: Portfolio construction with thesis-driven stock selection
  - Uses domain memory for consistent decision-making patterns
  - Returns structured portfolio with ticker, position, thesis, drivers, allocation

#### 3. API Layer (`app/api/`)
FastAPI-based REST API with WebSocket support:

- **Routes** (`routes/`):
  - `alts_router.py`: Alternative investment portfolio endpoints
  - `portfolio_router.py`: Portfolio operations and analysis
  - `user_routes.py`: User management
  - `websocket_router.py`: Real-time streaming for agent execution

- **Controllers** (`controller/`): Business logic layer between routes and services

#### 4. Data Layer
- **Database** (`app/db/`): PostgreSQL with SQLAlchemy/Peewee
- **Repositories** (`app/repositories/`): Data access layer
- **Models** (`app/models/`): Database models and schemas

## Key Design Patterns

### Agent Pattern
Agents follow a planning-then-execution workflow:
1. Initialize with system/user prompts and max iterations
2. Optionally create structured plan using PlanningTool (Pydantic models)
3. Execute tools in ReAct loop until final answer or iteration limit
4. Parse final output into structured format (Pydantic models)

### Memory-Enhanced Learning
- **Domain Memory**: Pre-loaded patterns (e.g., CIO portfolio construction knowledge)
- **Episodic Memory**: Recent successful tool executions, refreshed every N iterations

### Tool Registration
Each agent registers relevant tools via `register_*_tools(agent)` functions that:
1. Define tool schemas (OpenAI function calling format)
2. Map tool names to Python callables
3. Provide argument parsing and validation

## Development Guidelines

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

## Branching Strategy

- `main`: Production-ready code
- `dev`: Integration branch (current active branch)
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation
- `refactor/*`: Code refactoring
- `test/*`: Test additions/fixes

## External Dependencies

- **FastAPI**: Web framework and API
- **Pydantic**: Data validation and settings management
- **PostgreSQL**: Database
- **OpenAI/Claude/Grok**: LLM providers for agents
- **Pandas/NumPy/SciPy**: Data analysis and numerical computation

### Essential Tools
- **Pydantic**: https://docs.pydantic.dev/
- **FastAPI**: https://fastapi.tiangolo.com/

## Important Files

- `main.py`: FastAPI application entrypoint
- `requirements.txt`: Python dependencies
- `.env`: Environment variables (API keys, DB credentials) - **NEVER COMMIT**
- `app/core/agentic_framework/base_agent/agent.py`: Core agent implementation
- `app/core/agentic_framework/base_agent/tasks/models.py`: Task/planning data models

## Important Rules

- Never create a README.md for a specific functionality or new new unless specifically requested
- Do not be afraid to disagree with me. If I say something or ask you a question do not hesitate to correct me. The most important thing is being correct and writing effective code
- Always use the fetch_bulk_price_data_for_tickers function for stock price fetching unless told otherwise