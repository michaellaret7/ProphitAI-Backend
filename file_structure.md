# ProphitAI Project File Structure

**Generated:** 2025-10-01

## Main Directory Overview

- **app/**: Core application code (agentic framework, API, domain logic, calculations, services)
- **notebooks/**: Jupyter notebooks for analysis and testing
- **tests/**: Test scripts and experimental code
- **planning/**: Project planning documents and TODO lists
- **.claude/**: Claude Code configuration and agent definitions
- **.cursor/**: Cursor IDE configuration

---

## Detailed Structure

```
ProphitAI/
│
├── .claude/
│   ├── agents/
│   │   ├── architect_review.md
│   │   ├── code_reviewer.md
│   │   ├── debugger.md
│   │   ├── explain.md
│   │   └── quality_enforcer.md
│   ├── commands/
│   │   └── fl_structure.md
│   ├── CLAUDE.md
│   └── settings.local.json
│
├── .cursor/
│   ├── error_fixing.mdc
│   ├── main_code_generation_rule.mdc
│   └── workflow_instructions.mdc
│
├── app/
│   ├── api/
│   │   ├── controller/
│   │   │   ├── alts.py
│   │   │   ├── portfolio_controller.py
│   │   │   └── user_controller.py
│   │   ├── routes/
│   │   │   ├── agent_runs_router.py
│   │   │   ├── alts_router.py
│   │   │   ├── portfolio_router.py
│   │   │   ├── user_routes.py
│   │   │   └── websocket_router.py
│   │   ├── testing/
│   │   │   ├── static/
│   │   │   │   └── test.html
│   │   │   ├── alts_testing.py
│   │   │   ├── portfolio_testing.py
│   │   │   └── user_testing.py
│   │   ├── portfolio.py
│   │   ├── prophit_alts.py
│   │   ├── response_envelope.py
│   │   ├── user.py
│   │   └── websocket.py
│   │
│   ├── core/
│   │   ├── agentic_framework/
│   │   │   ├── agent_output/
│   │   │   │   ├── agent_messages.json
│   │   │   │   └── task_state.json
│   │   │   ├── base_agent/
│   │   │   │   ├── core/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── arg_parser.py
│   │   │   │   │   ├── logger.py
│   │   │   │   │   └── utilities.py
│   │   │   │   ├── events/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── manager.py
│   │   │   │   ├── memory/
│   │   │   │   │   ├── memory_store/
│   │   │   │   │   │   ├── domain_memory/
│   │   │   │   │   │   │   ├── beverages_memory.json
│   │   │   │   │   │   │   ├── cio_memory.json
│   │   │   │   │   │   │   ├── consumer_staples_distribution_and_retail_memory.json
│   │   │   │   │   │   │   ├── cro_memory.json
│   │   │   │   │   │   │   ├── food_products_memory.json
│   │   │   │   │   │   │   ├── household_products_memory.json
│   │   │   │   │   │   │   ├── optimizer_memory.json
│   │   │   │   │   │   │   ├── personal_care_products_memory.json
│   │   │   │   │   │   │   └── tobacco_memory.json
│   │   │   │   │   │   ├── episodic_memory.json
│   │   │   │   │   │   └── tool_error_memory.json
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── domain_memory.py
│   │   │   │   │   ├── episodic_memory.py
│   │   │   │   │   └── error_memory.py
│   │   │   │   ├── tasks/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── execution_engine.py
│   │   │   │   │   ├── manager.py
│   │   │   │   │   ├── models.py
│   │   │   │   │   └── validator.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py
│   │   │   │   └── tool_registry.py
│   │   │   ├── evaluation/
│   │   │   │   ├── hallucinations.md
│   │   │   │   └── plan.md
│   │   │   ├── tests/
│   │   │   │   └── tool_error.py
│   │   │   └── tool_lib/
│   │   │       ├── agent_specific_tools/
│   │   │       │   ├── cio.py
│   │   │       │   ├── cro.py
│   │   │       │   ├── industry.py
│   │   │       │   └── optimizer.py
│   │   │       ├── base_tools/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── calculator.py
│   │   │       │   ├── planning_tool.py
│   │   │       │   └── search_engine.py
│   │   │       ├── data_tools/
│   │   │       │   ├── industry_factors.py
│   │   │       │   ├── repository.py
│   │   │       │   ├── stock_screener.py
│   │   │       │   ├── sub_industry_factors.py
│   │   │       │   └── ticker_fundamentals.py
│   │   │       ├── portfolio_tools/
│   │   │       │   ├── beta.py
│   │   │       │   ├── build_allocations.py
│   │   │       │   ├── concentration.py
│   │   │       │   ├── corr_matrix.py
│   │   │       │   ├── factor_tilts.py
│   │   │       │   ├── group_performance.py
│   │   │       │   ├── performance.py
│   │   │       │   ├── returns.py
│   │   │       │   └── ticker_performance.py
│   │   │       ├── risk_tools/
│   │   │       │   ├── asset_risk_contrib.py
│   │   │       │   ├── cov_matrix.py
│   │   │       │   ├── drawdown_profile.py
│   │   │       │   ├── pairwise_corr_analysis.py
│   │   │       │   ├── stress_test.py
│   │   │       │   └── vol_es.py
│   │   │       └── ticker_tools/
│   │   │           ├── factors.py
│   │   │           ├── performance.py
│   │   │           └── weekly_returns.py
│   │   │
│   │   └── calculations/
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   ├── config.py
│   │       │   ├── data_service.py
│   │       │   ├── exceptions.py
│   │       │   ├── helpers.py
│   │       │   └── models.py
│   │       ├── factors/
│   │       │   ├── __init__.py
│   │       │   ├── config.py
│   │       │   ├── growth.py
│   │       │   ├── momentum.py
│   │       │   ├── quality.py
│   │       │   ├── value.py
│   │       │   └── volatility.py
│   │       ├── machine_learning/
│   │       │   └── expected_annualized_return.py
│   │       ├── performance/
│   │       │   ├── __init__.py
│   │       │   └── calculator.py
│   │       ├── portfolio/
│   │       │   ├── allocations/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── allocator.py
│   │       │   │   ├── optimizer.py
│   │       │   │   └── rebalancer.py
│   │       │   ├── __init__.py
│   │       │   ├── concentration.py
│   │       │   ├── correlation.py
│   │       │   ├── factor_tilt.py
│   │       │   └── utils.py
│   │       ├── returns/
│   │       │   ├── __init__.py
│   │       │   └── calculator.py
│   │       ├── risk/
│   │       │   ├── __init__.py
│   │       │   ├── calculator.py
│   │       │   └── liquidity.py
│   │       ├── sectors/
│   │       │   ├── base.py
│   │       │   ├── industry.py
│   │       │   ├── sector.py
│   │       │   └── sub_industry.py
│   │       ├── stress_test/
│   │       │   ├── engine.py
│   │       │   ├── pairwise_corr_analysis.py
│   │       │   ├── performance_analysis.py
│   │       │   ├── runner.py
│   │       │   └── scenarios.py
│   │       ├── technical/
│   │       │   ├── __init__.py
│   │       │   └── indicators.py
│   │       └── __init__.py
│   │
│   ├── db/
│   │   ├── core/
│   │   │   ├── add_etf.py
│   │   │   ├── build_price_table.py
│   │   │   ├── db_config.py
│   │   │   ├── market_data_models.py
│   │   │   ├── prophit_alts_models.py
│   │   │   ├── pull_fmp_data.py
│   │   │   ├── schema.json
│   │   │   └── user_data_models.py
│   │   ├── jobs/
│   │   │   ├── fundamental_data.py
│   │   │   ├── price_table.py
│   │   │   └── ticker_table.py
│   │   └── monitor/
│   │       ├── health_check.py
│   │       └── query_performance_check.py
│   │
│   ├── domain/
│   │   ├── portfolio_operations/
│   │   │   ├── builder/
│   │   │   │   └── main.py
│   │   │   └── optimization/
│   │   │       ├── optimizer/
│   │   │       │   ├── agent.py
│   │   │       │   ├── prompts.py
│   │   │       │   └── tool_registry.py
│   │   │       └── main.py
│   │   ├── prophit_alts/
│   │   │   └── consumer_staples_fund/
│   │   │       ├── build_portfolio/
│   │   │       │   ├── cio/
│   │   │       │   │   ├── simulation/
│   │   │       │   │   │   ├── __init__.py
│   │   │       │   │   │   ├── config.py
│   │   │       │   │   │   └── simulation_agent.py
│   │   │       │   │   ├── agent.py
│   │   │       │   │   ├── prompts.py
│   │   │       │   │   └── tool_registry.py
│   │   │       │   ├── cro/
│   │   │       │   │   ├── agent.py
│   │   │       │   │   ├── portfolio_revisions.json
│   │   │       │   │   ├── prompts.py
│   │   │       │   │   └── tool_registry.py
│   │   │       │   ├── final_portfolio/
│   │   │       │   │   ├── cio.py
│   │   │       │   │   └── prompts.py
│   │   │       │   └── industry_agents/
│   │   │       │       ├── agents.py
│   │   │       │       ├── prompts.py
│   │   │       │       └── tool_registry.py
│   │   │       └── manage_portfolio/
│   │   │           └── drawdown_management.py
│   │   └── prophit_gpt/
│   │       └── main.py
│   │
│   ├── models/
│   │   ├── performance_models.py
│   │   ├── phase_two_models.py
│   │   ├── portfolio_models.py
│   │   └── style_factors_models.py
│   │
│   ├── repositories/
│   │   ├── etf_data.py
│   │   ├── fundamental_data.py
│   │   ├── news_data.py
│   │   ├── portfolio_data.py
│   │   ├── price_data.py
│   │   ├── prophit_alts_data.py
│   │   ├── ratings_data.py
│   │   ├── transcripts_data.py
│   │   └── user_data.py
│   │
│   ├── services/
│   │   ├── agent_runs.py
│   │   ├── prophit_alts_service.py
│   │   └── websocket_manager.py
│   │
│   └── utils/
│       ├── decorators/
│       │   ├── database.py
│       │   ├── price_data.py
│       │   ├── timer.py
│       │   └── tool_validation.py
│       ├── __init__.py
│       ├── choose_model_and_client.py
│       ├── gpt_parser.py
│       ├── logging_config.py
│       ├── serialize_output.py
│       ├── simulation_utils.py
│       ├── ticker_utils.py
│       ├── token_count.py
│       └── validation_utils.py
│
├── notebooks/
│   ├── data.ipynb
│   ├── portfolio_analysis.ipynb
│   ├── test_repository_data_dates.ipynb
│   ├── testing.ipynb
│   └── user_db.ipynb
│
├── planning/
│   ├── error_fixer.md
│   ├── structure_migration.md
│   └── todo.md
│
├── tests/
│   ├── hedge_fund_stuff/
│   │   ├── Hedge_fund_portfolio_construction.py
│   │   └── Hedge_fund_risk_management.py
│   ├── vector_storage/
│   │   ├── INDEX.yml
│   │   ├── build.py
│   │   ├── corpus.faiss
│   │   ├── corpus.txt
│   │   ├── docs.jsonl
│   │   ├── embeddings.npy
│   │   └── query.py
│   ├── alpaca_trade.py
│   ├── cluster_analysis.py
│   ├── retail-fund-code.py
│   └── streaming_data.py
│
├── .env
├── .env.example
├── .gitignore
├── README.md
├── file_structure.md
├── main.py
└── requirements.txt
```

---

## Key Components

### Core Application (`app/`)
- **agentic_framework/**: BaseAgent, memory systems, tool libraries, task management
- **calculations/**: Financial calculations (portfolio, risk, performance, factors)
- **api/**: FastAPI routes, controllers, WebSocket support
- **domain/**: Domain-specific agents (CIO, CRO, Industry agents, ProphitAlts)
- **db/**: Database models, jobs, and monitoring
- **repositories/**: Data access layer
- **services/**: Business logic and orchestration
- **utils/**: Shared utilities and decorators

### Configuration & Planning
- **.claude/**: Agent definitions and commands for Claude Code
- **planning/**: Project planning and documentation
- **notebooks/**: Jupyter notebooks for analysis and experimentation
