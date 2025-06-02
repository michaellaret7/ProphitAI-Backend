├── backend/
│   ├── output/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── analysts/
│   │   │   ├── __init__.py
│   │   │   ├── equityAnalysts.py
│   │   │   └── macroAnalysts.py
│   │   ├── backtest/
│   │   │   ├── backtest_helpers.py
│   │   │   └── backtest_run.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── FundamentalData.py
│   │   │   ├── PortfolioData.py
│   │   │   ├── update_fundamental_predictions.py
│   │   │   ├── update_stock_data.py
│   │   │   ├── user_information.py
│   │   │   ├── database/
│   │   │   │   ├── database_prices_schema_update.py
│   │   │   │   ├── database_schema_update.py
│   │   │   │   ├── database_schemas.json
│   │   │   │   └── database_schemas_prices.json
│   │   │   ├── final_portfolio_data/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── store_final_portfolio.py
│   │   │   │   ├── store_portfolio_sector_allocations.py
│   │   │   │   └── store_user_information.py
│   │   │   ├── fundamental_report/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── generate_and_store_sector_averages.py
│   │   │   │   ├── generate_fundamental_report.py
│   │   │   │   └── store_fundamental_report.py
│   │   │   └── user_portfolio_data/
│   │   │       ├── __init__.py
│   │   │       ├── fetch_ibkr_holdings.py
│   │   │       ├── retrieve_and_store_portfolio_data.py
│   │   │       ├── store_user_positions.py
│   │   │       └── update_user_holdings.py
│   │   ├── portfolio_builder/
│   │   ├── portfolio_optimization/
│   │   │   ├── __init__.py
│   │   │   ├── runner.py
│   │   │   ├── phase_one/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── phase_one_formatting.py
│   │   │   │   ├── phase_one_prompts.py
│   │   │   │   ├── phase_one_run.py
│   │   │   │   └── phase_one_validation.py
│   │   │   └── phase_two/
│   │   │       ├── __init__.py
│   │   │       ├── data_retrieval.py
│   │   │       ├── phase_two_calculations.py
│   │   │       ├── phase_two_prompts.py
│   │   │       ├── phase_two_run.py
│   │   │       └── retrieve_fundamental_report.py
│   │   ├── prophitai_gpt/
│   │   │   ├── gpt.py
│   │   │   ├── dataRetrievalTools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── portfolioData.py
│   │   │   │   └── retrieve_financial_metrics.py
│   │   │   ├── functionSchemas/
│   │   │   │   └── tools.py
│   │   │   └── placeOrders/
│   │   │       ├── exitPosition.py
│   │   │       └── longOrder.py
│   │   ├── research/
│   │   │   ├── cache_research.py
│   │   │   ├── equity_research_analysts.py
│   │   │   └── macro_research_analyst.py
│   │   ├── stress_test_agent/
│   │   │   ├── stress_test_agent_class.py
│   │   │   ├── stress_test_agent_run.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── get_data.py
│   │   │       └── tool_registry.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── caching.py
│   │       ├── choose_model_and_client.py
│   │       ├── data_retrieval.py
│   │       ├── database.py
│   │       ├── determine_etf.py
│   │       ├── file_utils.py
│   │       ├── financial_calculations.py
│   │       ├── formatting.py
│   │       ├── ib_utils.py
│   │       ├── logging_config.py
│   │       ├── retrieve_portfolio_from_db.py
│   │       └── ticker_utils.py
│   └── testing/
│       ├── AgentSDKWorks.py
│       ├── FinalSectorSheet.xlsx
│       ├── react_agent_class.py
│       ├── react_agent_run.py
│       ├── recentOutput.txt
│       ├── sandbox.py
│       └── buildDB.py
├── frontend/
│   ├── dist/
│   ├── node_modules/
│   ├── public/
│   └── src/
│       ├── assets/
│       │   └── logos/
│       └── components/
├── .env
├── .gitignore
├── file_structure.md
├── prompt_testing.md
└── requirements.txt