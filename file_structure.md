├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── README.md
│   ├── jobs/
│   │   ├── update_database_prices_schema.py
│   │   ├── update_database_schema.py
│   │   ├── update_fundamental_predictions.py
│   │   ├── update_fundamentals.py
│   │   └── update_stock_data.py
│   ├── output/
│   │   └── portfolio_optimization_*.txt
│   └── src/
│       ├── __init__.py
│       ├── agents/
│       │   ├── __init__.py
│       │   └── stress_test_agent/
│       │       ├── stress_test_agent_class.py
│       │       ├── stress_test_agent_run.py
│       │       └── tools/
│       │           ├── __init__.py
│       │           ├── get_data.py
│       │           └── tool_registry.py
│       ├── analysts/
│       │   ├── __init__.py
│       │   ├── analyst_research/
│       │   │   ├── cache_research.py
│       │   │   ├── equity_research_analysts.py
│       │   │   └── macro_research_analyst.py
│       │   ├── equity_analysts.py
│       │   └── macro_analysts.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── portfolio.py
│       │   ├── prophitgpt.py
│       │   └── runner.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── dependencies.py
│       │   ├── models.py
│       │   └── routes.py
│       ├── calculations/
│       │   ├── factor_calculations/
│       │   │   ├── growth_factor_calculations.py
│       │   │   ├── momentum_factor_calculations.py
│       │   │   ├── quality_factor_calculations.py
│       │   │   ├── value_factor_calculations.py
│       │   │   └── volatility_factor_calculations.py
│       │   ├── performance_calculations/
│       │   │   ├── portfolio_performance_calculations.py
│       │   │   └── ticker_performance_calculations.py
│       │   └── returns_calculations/
│       │       ├── portfolio_returns_calculations.py
│       │       ├── returns_under_stress_calculations.py
│       │       └── ticker_returns_calculations.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── database/
│       │   │   ├── database_schemas_prices.json
│       │   │   └── database_schemas.json
│       │   ├── fundamental_report/
│       │   │   ├── __init__.py
│       │   │   ├── generate_and_store_sector_averages.py
│       │   │   ├── generate_fundamental_report.py
│       │   │   └── store_fundamental_report.py
│       │   ├── user_information.py
│       │   └── user_portfolio_data/
│       │       ├── __init__.py
│       │       ├── fetch_ibkr_holdings.py
│       │       ├── store_user_positions.py
│       │       └── update_user_holdings.py
│       ├── data_models/
│       │   ├── performance_models.py
│       │   ├── phase_two_models.py
│       │   ├── portfolio_models.py
│       │   ├── style_factors_models.py
│       │   └── user_models.py
│       ├── portfolio_optimization/
│       │   ├── __init__.py
│       │   ├── runner.py
│       │   ├── phase_one/
│       │   │   ├── __init__.py
│       │   │   ├── phase_one_formatting.py
│       │   │   ├── phase_one_prompts.py
│       │   │   ├── phase_one_run.py
│       │   │   └── phase_one_validation.py
│       │   └── phase_two/
│       │       ├── __init__.py
│       │       ├── phase_two_extract_assets_classes.py
│       │       ├── phase_two_filters.py
│       │       ├── phase_two_performance_metrics.py
│       │       ├── phase_two_prompts.py
│       │       ├── phase_two_run_llm.py
│       │       └── phase_two_run.py
│       ├── prophit_alts/
│       │   ├── poc.py
│       │   ├── consumer_staples_fund/
│       │   │   ├── build_portfolio/
│       │   │   │   ├── distribution_and_retail/
│       │   │   │   │   ├── distribution_and_retail_agent.py
│       │   │   │   │   ├── prompts.py
│       │   │   │   │   └── trading_strategy_analysis_*.txt
│       │   │   │   └── tobacco_industry/
│       │   │   └── manage_portfolio/
│       │   └── core/
│       │       ├── base_agent_class.py
│       │       ├── equip_tools.py
│       │       └── tools.py
│       ├── prophitai_gpt/
│       │   ├── gpt.py
│       │   ├── dataRetrievalTools/
│       │   │   ├── __init__.py
│       │   │   └── retrieve_financial_metrics.py
│       │   ├── functionSchemas/
│       │   │   └── tools.py
│       │   └── placeOrders/
│       │       ├── exitPosition.py
│       │       └── longOrder.py
│       ├── repositories/
│       │   ├── base_repository.py
│       │   ├── fundamental_data/
│       │   │   └── fundamental_repository.py
│       │   ├── market_data/
│       │   │   ├── equity_price_repository.py
│       │   │   ├── etf_price_repository.py
│       │   │   └── ticker_repository.py
│       │   ├── portfolio/
│       │   │   ├── created_portfolio_repository.py
│       │   │   └── push_created_portfolio_repository.py
│       │   └── user/
│       │       ├── user_info_repository.py
│       │       └── user_portfolio_repository.py
│       └── utils/
│           ├── __init__.py
│           ├── caching.py
│           ├── choose_model_and_client.py
│           ├── database.py
│           ├── determine_etf.py
│           ├── file_utils.py
│           ├── financial_calculations.py
│           ├── formatting.py
│           ├── ib_utils.py
│           ├── logging_config.py
│           ├── portfolio_analysis.py
│           ├── push_full_hist_data.py
│           └── ticker_utils.py
│   └── testing/
│       ├── All_US_ETFs.xlsx
│       ├── buildDB.py
│       ├── react_agent_class.py
│       ├── react_agent_run.py
│       ├── test_price_data.py
│       └── hedge_fund_stuff/
│           ├── hedge_fund_portfolio_construction.py
│           └── hedge_fund_risk_management.py
├── frontend/
│   ├── src
├── file_structure.md
├── prompt_testing.md
├── README.md
├── requirements.txt
└── roadmap.md