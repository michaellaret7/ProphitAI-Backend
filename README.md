# ProphitAI

<p align="left">
  <img src="frontend/src/assets/logo_smaller.png" alt="ProphitAI Logo"/>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.13.5-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)

> An AI-powered institutional-grade portfolio management platform leveraging autonomous agents for portfolio construction, risk analysis, and financial research.

## Overview

ProphitAI is a sophisticated portfolio management platform that uses a state-of-the-art agentic framework powered by multiple LLM providers (OpenAI, Claude, Grok). The system employs autonomous agents that collaborate to construct portfolios, analyze risk, perform stress testing, and conduct financial research—all while maintaining institutional-grade rigor.

**Key Innovation:** Unlike traditional portfolio management tools, ProphitAI uses a **ReAct (Reasoning + Acting) pattern** with specialized domain agents that have memory systems, tool-calling capabilities, and structured planning workflows.

## Core Features

### Autonomous Agentic Framework
- **BaseAgent Architecture**: Implements ReAct pattern with native tool-calling across OpenAI, Claude, and Grok
- **Task Management**: Hierarchical TodoList system with MainTask/SubTask tracking
- **Memory Systems**: Domain memory for agent-specific knowledge + episodic memory for learning from successful executions
- **Specialized Agents**: CIO (portfolio construction), CRO (risk analysis), Industry analysts, Macro agents, AI Watchlist agents
- **Portfolio Optimizer Agent**: Automated portfolio optimization with multiple strategies

### Portfolio Management
- **AI-Driven Construction**: Thesis-driven stock selection with structured allocation recommendations
- **Alternative Investments**: Specialized funds (Consumer Staples, etc.) with sector-specific agents
- **Portfolio Allocation**: Intelligent allocation engine with position sizing
- **Performance Analytics**: Portfolio metrics, concentration analysis, factor tilts, beta calculations
- **Correlation Analysis**: Multi-asset correlation matrices and group performance tracking

### Risk Management
- **Covariance & VaR/ES**: Statistical risk measures and portfolio volatility analysis
- **Stress Testing**: Scenario-based stress testing with custom market conditions
- **Drawdown Analysis**: Historical drawdown profiles and recovery periods
- **Asset Risk Contribution**: Identify portfolio risk concentrations
- **Risk Scores**: Comprehensive risk scoring system

### Data & Analytics
- **Market Data**: Real-time and historical price data via bulk fetching
- **Fundamentals**: Company financials, ratios, and screening tools
- **Factor Analysis**: Volatility factors, industry/sub-industry analytics
- **Technical Indicators**: Comprehensive technical analysis toolkit
- **Market Regime Detection**: ML-powered market regime classification
- **Sector Analytics**: Sector and industry performance analysis
- **Crypto Data**: Cryptocurrency market data and analytics
- **ETF Analytics**: ETF analysis and screening

### Macro Research
- **Macro Agent**: AI-powered macroeconomic research and analysis
- **Economic Indicators**: Integration with economic data sources
- **Market Regime Analysis**: Automated market environment classification

### API & Integration
- **RESTful API**: FastAPI-based with automatic OpenAPI/Swagger documentation
- **WebSocket Support**: Real-time streaming for agent execution and live updates
- **Alpaca Integration**: Broker integration for trading
- **Redis Caching**: High-performance caching layer
- **Database**: PostgreSQL with SQLAlchemy/Peewee ORM and Alembic migrations
- **Messaging System**: Encrypted messaging infrastructure

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy, Peewee
- **Migrations**: Alembic
- **Caching**: Redis
- **LLM Providers**: OpenAI, Claude (Anthropic), Grok
- **Data Science**: Pandas, NumPy, SciPy, scikit-learn
- **Portfolio Optimization**: Riskfolio-Lib
- **Validation**: Pydantic 2.x
- **Brokerage**: Alpaca

### Frontend
- **Framework**: React
- **Dev Server**: Vite (port 5173)

## Getting Started

### Prerequisites
- **Python**: 3.13.5
- **PostgreSQL**: Latest version
- **Redis**: For caching
- **Node.js**: For frontend development
- **API Keys**: OpenAI, Claude, Grok (optional)
- **Alpaca**: Account (for live trading)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ProphitAI.git
   cd ProphitAI
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\Activate.ps1

   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the root directory:
   ```env
   # Database
   DB_HOST=localhost
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_PORT=5432
   DB_NAME=prophitai

   # Redis
   REDIS_HOST=localhost
   REDIS_PORT=6379

   # LLM API Keys
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_claude_key
   GROK_API_KEY=your_grok_key

   # Alpaca
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ```

5. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb prophitai

   # Run migrations
   cd app/db/alembic_migration
   alembic upgrade head
   ```

### Running the Application

#### Backend (FastAPI)
```bash
# Ensure virtual environment is activated
python main.py
```
The API will be available at `http://localhost:8000`

- **Interactive API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

#### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```
The frontend will be available at `http://localhost:5173`

## Project Structure

```
ProphitAI/
├── app/
│   ├── api/                          # FastAPI routes and controllers
│   │   ├── routes/                   # API endpoints
│   │   │   ├── alts_router.py        # Alternative investment portfolios
│   │   │   ├── portfolio_router.py   # Portfolio operations
│   │   │   ├── ticker_router.py      # Ticker data and analysis
│   │   │   ├── fundamentals_router.py # Company fundamentals
│   │   │   ├── technical_router.py   # Technical analysis
│   │   │   ├── screener_router.py    # Stock screening
│   │   │   ├── macro_router.py       # Macroeconomic data
│   │   │   ├── crypto_router.py      # Cryptocurrency data
│   │   │   ├── etf_router.py         # ETF analytics
│   │   │   ├── news_router.py        # News and sentiment
│   │   │   ├── broker_router.py      # Broker integration
│   │   │   ├── agent_router.py       # Agent execution
│   │   │   ├── messaging_router.py   # Messaging system
│   │   │   ├── watchlist_routes.py   # Watchlist management
│   │   │   ├── user_routes.py        # User management
│   │   │   ├── cache_router.py       # Cache management
│   │   │   └── websocket_router.py   # Real-time streaming
│   │   └── controller/               # Business logic layer
│   │
│   ├── agents/                       # Standalone agents
│   │   └── macro_agent/              # Macroeconomic research agent
│   │
│   ├── core/
│   │   ├── agentic_framework/        # Core agent system
│   │   │   ├── base_agent/           # BaseAgent implementation
│   │   │   │   ├── agent.py          # ReAct pattern + tool calling
│   │   │   │   ├── tasks/            # Task management (TodoList, etc.)
│   │   │   │   ├── memory/           # Domain + episodic memory
│   │   │   │   └── core/             # Parser, logger, utilities
│   │   │   └── tool_lib/             # Tool library
│   │   │       ├── base_tools/       # Core utility tools
│   │   │       ├── data_tools/       # Market data, fundamentals
│   │   │       ├── risk_tools/       # Risk analytics
│   │   │       ├── portfolio_tools/  # Portfolio metrics
│   │   │       ├── ticker_tools/     # Ticker-specific analysis
│   │   │       ├── macro_tools/      # Macroeconomic tools
│   │   │       ├── sub_agents/       # Sub-agent orchestration
│   │   │       └── agent_specific_tools/  # CIO, CRO, Industry tools
│   │   │
│   │   ├── calculations/             # Core calculation engines
│   │   │   ├── core/                 # Core calculation utilities
│   │   │   ├── risk/                 # Risk calculations
│   │   │   │   └── scores/           # Risk scoring system
│   │   │   ├── performance/          # Performance metrics
│   │   │   ├── factors/              # Factor analysis
│   │   │   ├── returns/              # Return calculations
│   │   │   ├── portfolio/            # Portfolio calculations
│   │   │   │   └── allocator/        # Position allocation
│   │   │   ├── technical/            # Technical indicators
│   │   │   │   └── indicator_calcs/  # Indicator calculations
│   │   │   ├── stress_test/          # Stress testing
│   │   │   ├── sectors/              # Sector analytics
│   │   │   ├── market_regime/        # Market regime detection
│   │   │   └── machine_learning/     # ML models
│   │   │
│   │   └── search/                   # Search functionality
│   │       └── web_search/           # Web search integration
│   │
│   ├── domain/                       # Domain-specific agents
│   │   ├── prophit_alts/             # Alternative investment strategies
│   │   │   └── consumer_staples_fund/
│   │   │       ├── build_portfolio/  # CIO, CRO, Industry agents
│   │   │       └── manage_portfolio/ # Portfolio management
│   │   ├── prophit_gpt/              # Conversational AI assistant
│   │   ├── ai_watchlist/             # AI-powered watchlist agent
│   │   └── portfolio_operations/     # Portfolio operations
│   │       ├── builder/              # Portfolio builder
│   │       └── optimizer/            # Portfolio optimizer agent
│   │
│   ├── db/                           # Database layer
│   │   ├── core/                     # Core database models
│   │   ├── alembic_migration/        # Alembic migrations
│   │   ├── jobs/                     # Background jobs
│   │   │   └── macro_jobs/           # Macro data jobs
│   │   └── monitor/                  # Database monitoring
│   │
│   ├── redis/                        # Redis caching layer
│   ├── models/                       # Pydantic/SQLAlchemy models
│   ├── repositories/                 # Data access layer
│   ├── services/                     # Business services
│   └── utils/                        # Shared utilities
│       ├── decorators/               # Custom decorators
│       └── alpaca/                   # Alpaca integration
│
├── frontend/                         # React frontend application
│   └── src/
│
├── tests/                            # Test suite
├── main.py                           # FastAPI entrypoint
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment template
└── README.md                         # This file
```

## Key Design Patterns

### Agent Pattern
Agents follow a **planning-then-execution** workflow:
1. Initialize with system/user prompts and iteration limits
2. Create structured plan using `PlanningTool` (Pydantic models)
3. Execute tools in ReAct loop until completion
4. Parse final output into structured format

### Memory-Enhanced Learning
- **Domain Memory**: Pre-loaded patterns (e.g., CIO investment strategies)
- **Episodic Memory**: Stores recent successful tool executions for pattern recognition

### Tool Registration
Each agent registers relevant tools via `register_*_tools(agent)`:
1. Define tool schemas (OpenAI function calling format)
2. Map tool names to Python callables
3. Provide argument parsing and validation

## Development

### Branching Strategy
- `main` - Production-ready code
- `dev` - Integration branch (current active branch)
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring
- `test/*` - Test additions/fixes

### Code Philosophy
- **KISS**: Keep it simple—favor straightforward solutions
- **YAGNI**: You aren't gonna need it—build only what's needed
- **DRY**: Don't repeat yourself—single source of truth

### Code Constraints
- **Files**: Max 500 lines (split into modules if larger)
- **Functions**: Max 50 lines, single responsibility
- **Classes**: Max 100 lines, single concept
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes

### Documentation Requirements
- Module docstrings explaining purpose
- Complete docstrings for public functions
- Inline comments with `# Reason:` prefix for complex logic

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### Key Endpoints

#### Portfolio Operations
- `POST /api/portfolio/optimize` - Optimize portfolio allocations
- `GET /api/portfolio/{portfolio_id}/risk` - Get risk analytics
- `POST /api/portfolio/{portfolio_id}/stress-test` - Run stress tests

#### Alternative Investments
- `POST /api/alts/consumer-staples/build` - Build consumer staples portfolio
- `GET /api/alts/portfolios/{portfolio_id}` - Retrieve portfolio details

#### Market Data
- `GET /api/ticker/{symbol}` - Get ticker information
- `GET /api/price/{symbol}` - Get price data
- `GET /api/fundamentals/{symbol}` - Get company fundamentals
- `GET /api/technical/{symbol}` - Get technical indicators

#### Research & Analytics
- `GET /api/macro/indicators` - Get macroeconomic indicators
- `GET /api/screener/screen` - Screen stocks by criteria
- `GET /api/etf/{symbol}` - Get ETF analytics
- `GET /api/crypto/{symbol}` - Get cryptocurrency data
- `GET /api/news/{symbol}` - Get news and sentiment

#### Agent Execution
- `POST /api/agent/execute` - Execute agent task
- `WS /api/ws/agent-stream` - Real-time agent execution streaming

#### User & Watchlist
- `GET /api/watchlist` - Get user watchlists
- `POST /api/watchlist` - Create watchlist

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure code follows the project's style guidelines and includes appropriate tests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **FastAPI**: High-performance web framework
- **Pydantic**: Data validation and settings management
- **OpenAI/Anthropic/xAI**: LLM providers powering the agent framework
- **Riskfolio-Lib**: Portfolio optimization library
- **Redis**: In-memory caching
- **Alembic**: Database migrations
- **Alpaca**: Brokerage integration

---

**Built for institutional-grade portfolio management**
