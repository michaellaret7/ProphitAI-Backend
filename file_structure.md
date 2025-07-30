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
│       │   ├── returns_calculations/
│       │   │   ├── portfolio_returns_calculations.py
│       │   │   ├── returns_under_stress_calculations.py
│       │   │   └── ticker_returns_calculations.py
│       │   ├── risk_calculations/
│       │   │   ├── build_portfolio.py
│       │   │   ├── correlation_portfolio_builder.py
│       │   │   ├── portfolio_risk_calculations.py
│       │   │   └── ticker_risk_calculations.py
│       │   └── sector_calculations/
│       │       ├── industry_calculations.py
│       │       ├── sector_calculations.py
│       │       └── sub_industry_calculations.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── database/
│       │   │   ├── database_schemas_prices.json
│       │   │   └── database_schemas.json
│       │   └── user_information.py
│       ├── data_models/
│       │   ├── performance_models.py
│       │   ├── phase_two_models.py
│       │   └── style_factors_models.py
│       ├── db/
│       │   ├── core/
│       │   │   ├── build_price_table.py
│       │   │   ├── db_config.py
│       │   │   ├── market_data_models.py
│       │   │   ├── prophit_alts_models.py
│       │   │   ├── pull_fmp_data.py
│       │   │   ├── schema.json
│       │   │   └── user_data_models.py
│       │   ├── jobs/
│       │   │   ├── fundamental_data.py
│       │   │   ├── price_table.py
│       │   │   └── ticker_table.py
│       │   └── monitor/
│       │       ├── health_check.py
│       │       └── query_performance_check.py
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
│       │   ├── consumer_staples_fund/
│       │   │   ├── build_portfolio/
│       │   │   │   ├── cio_agent.py
│       │   │   │   ├── cro_agent.py
│       │   │   │   ├── industry_agents.py
│       │   │   │   ├── macro_agent.py
│       │   │   │   └── prompts/
│       │   │   │       ├── cio_agent_prompts.py
│       │   │   │       ├── macro_agent_prompts.py
│       │   │   │       └── industry_prompts/
│       │   │   │           ├── beverages.py
│       │   │   │           ├── distribution_and_retail.py
│       │   │   │           ├── food_products.py
│       │   │   │           ├── household_products.py
│       │   │   │           ├── personal_care_products.py
│       │   │   │           └── tobacco.py
│       │   │   └── manage_portfolio/
│       │   └── core/
│       │       ├── base_agent_class.py
│       │       └── tools/
│       │           ├── __init__.py
│       │           ├── data_wrapper_tool.py
│       │           └── search_engine_tool.py
│       ├── prophit_gpt/
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
│       │   ├── portfolio_data.py
│       │   ├── price_data.py
│       │   └── user_data.py
│       └── utils/
│           ├── __init__.py
│           ├── choose_model_and_client.py
│           ├── database.py
│           ├── determine_etf.py
│           ├── file_utils.py
│           ├── formatting.py
│           ├── ib_utils.py
│           ├── logging_config.py
│           ├── parsing_utils.py
│           ├── serialize_output.py
│           ├── ticker_utils.py
│           └── token_count.py
│   └── testing/
│       ├── All_US_ETFs.xlsx
│       ├── llm_dialogue.py
│       ├── react_agent_class.py
│       ├── react_agent_run.py
│       └── hedge_fund_stuff/
│           ├── hedge_fund_portfolio_construction.py
│           └── hedge_fund_risk_management.py
├── frontend/
│   ├── src
├── file_structure.md
├── README.md
├── requirements.txt
└── roadmap.md
