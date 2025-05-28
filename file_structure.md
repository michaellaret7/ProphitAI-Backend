├── src/ ← Python package root
│ ├── __init__.py
│ │
│ ├── analysts/ ← Rule-based analysts
│ │ ├── __init__.py
│ │ ├── equityAnalysts.py — equity research integration
│ │ └── macroAnalysts.py — macroeconomic logic
│ │
│ ├── backtest/ ← Backtesting engine
│ │ ├── backtest_helpers.py
│ │ └── backtest_run.py
│ │
│ ├── data/ ← DB schema & ETL for prices/fundamentals
│ │ ├── __init__.py
│ │ ├── FundamentalData.py — income/BS/CF pulls
│ │ ├── PortfolioData.py — single-stock & holdings fetch
│ │ ├── update_fundamental_predictions.py — updates predictive fundamentals
│ │ ├── update_stock_data.py — refreshes prices & fundamentals
│ │ ├── user_information.py — runtime user data
│ │ ├── database/
│ │ │ ├── database_prices_schema_update.py
│ │ │ ├── database_schema_update.py
│ │ │ ├── database_schemas.json
│ │ │ └── database_schemas_prices.json
│ │ ├── final_portfolio_data/
│ │ │ ├── __init__.py
│ │ │ ├── store_final_portfolio.py
│ │ │ ├── store_portfolio_sector_allocations.py
│ │ │ └── store_user_information.py
│ │ ├── fundamental_report/
│ │ │ ├── __init__.py
│ │ │ ├── generate_and_store_sector_averages.py
│ │ │ ├── generate_fundamental_report.py
│ │ │ └── store_fundamental_report.py
│ │ └── user_portfolio_data/
│ │
│ ├── portfolio_builder/ ← (placeholder for future work)
│ │
│ ├── portfolio_optimization/ ← Portfolio construction logic
│ │ ├── __init__.py
│ │ ├── runner.py — orchestrator / CLI entry
│ │ ├── phase_one/
│ │ │ ├── __init__.py
│ │ │ ├── phase_one_formatting.py
│ │ │ ├── phase_one_prompts.py
│ │ │ ├── phase_one_run.py — main driver for sector allocations
│ │ │ └── phase_one_validation.py
│ │ └── phase_two/
│ │   ├── __init__.py
│ │   ├── data_retrieval.py — price / statement pulls
│ │   ├── phase_two_calculations.py — DCF, CAGR, ratios
│ │   ├── phase_two_prompts.py
│ │   ├── phase_two_run.py — picks stocks per sector
│ │   └── retrieve_fundamental_report.py
│ │
│ ├── prophitai_gpt/ ← OpenAI agentic chatbot
│ │ ├── gpt.py — wrapper around ChatGPT calls
│ │ ├── dataRetrievalTools/
│ │ │ ├── __init__.py
│ │ │ ├── portfolioData.py
│ │ │ └── retrieve_financial_metrics.py
│ │ ├── functionSchemas/
│ │ │ └── tools.py — schema definitions for tools
│ │ └── placeOrders/
│ │   ├── exitPosition.py
│ │   └── longOrder.py
│ │
│ ├── research/ ← LLM-generated research drafts
│ │ ├── cache_research.py — pushes research to the database
│ │ ├── equity_research_analysts.py — writes stock research reports and stores them to the db
│ │ └── macro_research_analyst.py — writes macro commentary reports and stores them to the db
│ │
│ ├── stress_test_agent/ ← Agent for portfolio stress testing
│ │ ├── stress_test_agent_class.py
│ │ ├── stress_test_agent_run.py
│ │ └── tools/
│ │   ├── __init__.py
│ │   ├── get_data.py
│ │   └── tool_registry.py
│ │
│ └── utils/ ← Shared helpers
│   ├── __init__.py
│   ├── caching.py — TTL memoisation to disk/redis
│   ├── choose_model_and_client.py
│   ├── database.py — SQLite / Postgres helpers
│   ├── determine_etf.py — ticker classification
│   ├── file_utils.py — CSV/JSON convenience
│   ├── formatting.py — display helpers
│   ├── ib_utils.py — Interactive Brokers bridge
│   ├── logging_config.py
│   ├── retrieve_portfolio_from_db.py
│   └── ticker_utils.py
│
├── testing/ ← notebooks / sandboxes / demos
│ ├── AgentSDKWorks.py
│ ├── FinalSectorSheet.xlsx
│ ├── react_agent_class.py
│ ├── react_agent_run.py
│ ├── recentOutput.txt
│ └── sandbox.py
│
├── output/ ← generated reports, logs, etc.
│
└── .gitignore