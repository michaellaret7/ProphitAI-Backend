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

#### 1. Agentic Framework (`app/core/atlas/`)
The heart of ProphitAI - a sophisticated autonomous agent system for portfolio management:

- **BaseAgent** (`base_agent/agent.py`): Foundation for all specialized agents
  - Implements ReAct pattern with native tool-calling
  - Manages conversation history and token accounting
  - Handles iteration limits and stagnation detection
  - Supports multiple LLM providers (OpenAI, Claude, Grok)

- **Task Management System** (`base_agent/tasks/`):
  - `manager.py`: TodoList with MainTask/SubTask hierarchy
  - `plan_executor.py`: PlanExecutor for executing task plans
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

### Timezone Handling (CRITICAL)
**All datetime operations MUST use UTC time to ensure data consistency**

- **NEVER use `datetime.now()`** - This returns server local time and causes timezone misalignment
- **ALWAYS use `get_current_utc_time()`** from `app.utils.time_utils` for current time
- **Database stores UTC timestamps as naive datetimes** - All times are in UTC without timezone info
- **Price data from FMP API arrives in EST** - Converted to UTC before storage

#### Required Import
```python
from app.utils.time_utils import get_current_utc_time, get_utc_date_str, get_utc_days_ago
```

#### Available Functions
- `get_current_utc_time()` - Returns current UTC time as naive datetime
- `get_utc_date_str()` - Returns current UTC date as 'YYYY-MM-DD' string
- `get_utc_days_ago(days)` - Returns UTC time N days ago
- `get_utc_date_range(lookback_days)` - Returns (start_date, end_date) tuple

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
- DRY & Reuse: Check @helpers or @utils before coding. Refactor shared logic into pure, reusable functions to minimize duplication.
- Type Safety: Mandate Type Hints and explicit return types to ensure the codebase remains self-documenting and maintainable.
- Resource Efficiency: Use Context Managers for all I/O and prioritize vectorized operations for data-heavy tasks.

**Rules**
- When a function or class takes a portfolio as a parameter it should always be tickers: List[str] and holdings: List[int] 

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
- When in plan mode, evaluate whether the proposed plan is under-engineered, optimally engineered, or over-engineered.
- Before executing any task on the fly, assess its complexity to ensure your approach is optimally engineered.

## Branching Strategy

- `main`: Production-ready code
- `dev`: Integration branch (current active branch)
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

- **FastAPI**: Web framework and API
- **Pydantic**: Data validation and settings management
- **PostgreSQL**: Database
- **OpenAI/Claude/Grok**: LLM providers for agents
- **Pandas/NumPy/SciPy**: Data analysis and numerical computation

### Essential Tools
- **Pydantic**: https://docs.pydantic.dev/
- **FastAPI**: https://fastapi.tiangolo.com/

## Notion MCP Integration

The project uses Notion as the primary task management system via MCP (Model Context Protocol).

### Default User
- **Name**: Michael Laret
- **User ID**: `2d0d872b-594c-810c-a2a3-00022bfb858e`
- **Email**: michaellaret7@gmail.com

### CRITICAL RULES FOR CREATING NOTION TASKS

1. **ALWAYS assign tasks to Michael Laret** using his user ID: `2d0d872b-594c-810c-a2a3-00022bfb858e`

2. **ALWAYS create detailed page content** with:
   - `## Overview` - Brief description of the task
   - `## Implementation Steps` - Numbered steps with code examples where applicable
   - `## Files to Modify` - Checklist of files that need changes
   - `## Notes` - Any additional context, security considerations, or dependencies

3. **ALWAYS set a Due Date** - Default to today's date if not specified

4. **Example of a well-structured task page:**
```markdown
## Overview
Brief description of what needs to be done and why.

## Implementation Steps

### Step 1: [First Step Title]
Description and code example:
\`\`\`python
# code here
\`\`\`

### Step 2: [Second Step Title]
...

## Files to Modify
- [ ] `path/to/file1.py` - Description of changes
- [ ] `path/to/file2.py` - Description of changes

## Notes
- Important considerations
- Dependencies or prerequisites
```

---

### 1. Main Database (Project Tasks)
- **Page URL**: https://www.notion.so/Main-2df3ce2ecd8c8069aba0f1f6d77b4b44
- **Tasks Database URL**: https://www.notion.so/2df3ce2ecd8c8162a9d3ce6dbae3cf91
- **Data Source ID**: `2df3ce2e-cd8c-810f-be04-000b0b3bba3e`
- **Purpose**: Tasks organized by Project (e.g., ProphitChat, ProphitAlts)

| Property | Type | Options |
|----------|------|---------|
| Task name | title | - |
| Status | status | Not Started, In Progress, Done, Archived |
| Priority | select | Low, Medium, High, Urgent |
| Domain | select | Back End, Front End |
| Due | date | - |
| Assignee | person | - |
| Project | relation | Links to Projects database |
| Notes | text | - |
| Completed on | date | - |

---

### 2. Michael's ToDo's Database
- **URL**: https://www.notion.so/61b43a77bfb54b21867a2d9850d5eb1a
- **Data Source ID**: `ab3406fc-f65a-44a3-83d0-d6e1d4ea59ff`
- **Purpose**: Personal task tracking with categories

| Property | Type | Options |
|----------|------|---------|
| Task Name | title | - |
| Status | status | Not Started, In Progress, Done |
| Priority | select | Low, Medium, High, Urgent |
| Category | select | 🧾 Dad Assigned Items, ⚙️ Refactoring, 🔮 Agent Framework, 📚 Database Ops, 📖 General, 👷 Agents to Build |
| Task Type | multi_select | 🔮 Research, 🔧 New Tool, 🔌 API Endpoint, 🧹 Refactor, 🔎 Review, 🐛 Bug, 🌟 New Feature, 📐Fix |
| Effort Level | select | Low, Medium, High |
| Due Date | date | - |
| Assignee | person | - |
| Project | relation | Links to Projects |
| Notes | text | - |

---

### 3. Backend Sprints Database
- **Page URL**: https://www.notion.so/Backend-Sprints-2df3ce2ecd8c8014856ce927f80a94e3
- **Tasks Database URL**: https://www.notion.so/2df3ce2ecd8c81c0a071f553c9da9524
- **Data Source ID**: `2df3ce2e-cd8c-81bf-91ca-000b75b96617`
- **Purpose**: Sprint-based backend development tasks

| Property | Type | Options |
|----------|------|---------|
| Task name | title | - |
| Status | status | Not Started, In Progress, Done, Archived |
| Priority | select | Low, Medium, High |
| Due | date | - |
| Assignee | person | - |
| Project | relation | Links to Sprint Projects |
| Completed on | date | - |
| Sub-tasks | relation | Self-referencing for task hierarchy |
| Parent-task | relation | Self-referencing for task hierarchy |

---

### MCP Tools Usage

**Search for tasks:**
```
mcp__notion__notion-search with query="task name or keyword"
```

**Fetch database schema:**
```
mcp__notion__notion-fetch with id="database URL"
```

**Create a new task:**
```
mcp__notion__notion-create-pages with:
- parent: {"type": "data_source_id", "data_source_id": "<data_source_id>"}
- pages: [{"properties": {...}}]
```

**Update task properties:**
```
mcp__notion__notion-update-page with:
- data: {"page_id": "<page_id>", "command": "update_properties", "properties": {...}}
```

**Add content to task page:**
```
mcp__notion__notion-update-page with:
- data: {"page_id": "<page_id>", "command": "replace_content", "new_str": "<markdown content>"}
```

### Quick Reference: Creating a Task

```python
# 1. Create the task with properties
mcp__notion__notion-create-pages(
    parent={"type": "data_source_id", "data_source_id": "2df3ce2e-cd8c-810f-be04-000b0b3bba3e"},
    pages=[{
        "properties": {
            "Task name": "Task title here",
            "Status": "Not Started",
            "Priority": "Medium",
            "Domain": "Back End",
            "Assignee": "[\"2d0d872b-594c-810c-a2a3-00022bfb858e\"]",
            "date:Due:start": "2026-01-05",
            "date:Due:is_datetime": 0,
            "Project": "[\"<project_page_url>\"]",
            "Notes": "Brief notes"
        }
    }]
)

# 2. Add detailed content to the page
mcp__notion__notion-update-page(
    data={
        "page_id": "<returned_page_id>",
        "command": "replace_content",
        "new_str": "## Overview\n\n..."
    }
)
```

## Important Files

- `main.py`: FastAPI application entrypoint
- `requirements.txt`: Python dependencies
- `.env`: Environment variables (API keys, DB credentials) - **NEVER COMMIT**
- `app/core/atlas/base_agent/agent.py`: Core agent implementation
- `app/core/atlas/base_agent/tasks/models.py`: Task/planning data models

## Important Rules

- Never create a README.md for a specific functionality or new new unless specifically requested
- If you have any intermittent thoughts that you want to write down/take notes on write them in the .claude/NOTEPAD.md file
- Do not create an excess of test files.
  --> For example sometimes you create a test file and then a fixed test file. Just create and fix the one
- Do not be afraid to disagree with me. If I say something or ask you a question do not hesitate to correct me. The most important thing is being correct and writing effective code
- Always use the fetch_bulk_price_data_for_tickers function for stock price fetching unless told otherwise
- Never, create **Backwards Compatibility**, if there is a change that needs to be made, built the new solution and change everything that it affects. Backwards compatibilty violates our design principles. 
- Do not ever create code functionality where we have to use arg commands to run it properly --> for example: tests/hrp_comb.py --mode long-only
- Use the LSP Pyright server whenever you can