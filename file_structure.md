├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── src/
│   │   ├── __init__.py
│   │   ├── agentic_framework/
│   │   │   ├── agent_output/
│   │   │   │   ├── agent_messages.json
│   │   │   │   └── task_state.json
│   │   │   ├── base_agent/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py
│   │   │   │   ├── core/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── arg_parser.py
│   │   │   │   │   ├── logger.py
│   │   │   │   │   └── utilities.py
│   │   │   │   ├── events/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── manager.py
│   │   │   │   ├── memory/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── error_memory.py
│   │   │   │   │   ├── memory_store/
│   │   │   │   │   │   ├── semantic_memory/
│   │   │   │   │   │   │   └── cro_memory.json
│   │   │   │   │   │   └── tool_error_memory.json
│   │   │   │   │   └── semantic_memory.py
│   │   │   │   └── tasks/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── execution_engine.py
│   │   │   │       ├── manager.py
│   │   │   │       ├── models.py
│   │   │   │       └── validator.py
│   │   │   └── base_tools/
│   │   │       ├── __init__.py
│   │   │       ├── calculator.py
│   │   │       ├── data_wrapper_prompt.py
│   │   │       ├── data_wrapper_tool.py
│   │   │       ├── planning_tool.py
│   │   │       └── search_engine_tool.py
│   │   ├── analysts/
│   │   │   ├── __init__.py
│   │   │   ├── analyst_research/
│   │   │   │   ├── cache_research.py
│   │   │   │   ├── equity_research_analysts.py
│   │   │   │   └── macro_research_analyst.py
│   │   │   ├── equity_analysts.py
│   │   │   └── macro_analysts.py
│   │   ├── api/
│   │   │   ├── controller/
│   │   │   │   ├── prophit_alts_controller.py
│   │   │   │   └── user_controller.py
│   │   │   ├── routes/
│   │   │   │   ├── prophit_alts_router.py
│   │   │   │   └── user_routes.py
│   │   │   ├── prophit_alts.py
│   │   │   ├── response_envelope.py
│   │   │   ├── testing/
│   │   │   │   ├── prophit_alts_testing.py
│   │   │   │   └── user_testing.py
│   │   │   └── user.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── audit.py
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   ├── models.py
│   │   │   └── sso.py
│   │   ├── calculations/
│   │   │   ├── build_corr_portfolio/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── correlation_analyzer.py
│   │   │   │   ├── correlation_portfolio_builder.py
│   │   │   │   ├── data_fetcher.py
│   │   │   │   ├── performance_metrics.py
│   │   │   │   ├── portfolio_optimizer.py
│   │   │   │   ├── portfolio_reporter.py
│   │   │   │   ├── portfolio_visualizer.py
│   │   │   │   ├── returns_calculator.py
│   │   │   │   └── risk_metrics.py
│   │   │   ├── factor_calculations/
│   │   │   │   ├── growth_factor_calculations.py
│   │   │   │   ├── momentum_factor_calculations.py
│   │   │   │   ├── quality_factor_calculations.py
│   │   │   │   ├── value_factor_calculations.py
│   │   │   │   └── volatility_factor_calculations.py
│   │   │   ├── performance_calculations/
│   │   │   │   ├── portfolio_performance_calculations.py
│   │   │   │   └── ticker_performance_calculations.py
│   │   │   ├── returns_calculations/
│   │   │   │   ├── portfolio_returns_calculations.py
│   │   │   │   └── ticker_returns_calculations.py
│   │   │   ├── risk_calculations/
│   │   │   │   ├── portfolio_risk_calculations.py
│   │   │   │   └── ticker_risk_calculations.py
│   │   │   └── sector_calculations/
│   │   │       ├── industry_calculations.py
│   │   │       ├── sector_calculations.py
│   │   │       └── sub_industry_calculations.py
│   │   ├── calculations_v2/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   ├── data_service.py
│   │   │   │   ├── exceptions.py
│   │   │   │   └── models.py
│   │   │   ├── factors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── growth.py
│   │   │   │   ├── momentum.py
│   │   │   │   ├── quality.py
│   │   │   │   ├── value.py
│   │   │   │   └── volatility.py
│   │   │   ├── performance/
│   │   │   │   ├── __init__.py
│   │   │   │   └── calculator.py
│   │   │   ├── portfolio/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── build/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── builder.py
│   │   │   │   │   ├── example_usage.py
│   │   │   │   │   └── optimizer.py
│   │   │   │   └── correlation.py
│   │   │   ├── returns/
│   │   │   │   ├── __init__.py
│   │   │   │   └── calculator.py
│   │   │   ├── risk/
│   │   │   │   ├── __init__.py
│   │   │   │   └── calculator.py
│   │   │   ├── sectors/
│   │   │   │   ├── industry.py
│   │   │   │   ├── sector.py
│   │   │   │   └── sub_industry.py
│   │   │   └── technical/
│   │   │       ├── __init__.py
│   │   │       └── indicators.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── database_schemas_prices.json
│   │   │   │   └── database_schemas.json
│   │   │   └── user_information.py
│   │   ├── data_models/
│   │   │   ├── performance_models.py
│   │   │   ├── phase_two_models.py
│   │   │   └── style_factors_models.py
│   │   ├── db/
│   │   │   ├── core/
│   │   │   │   ├── add_etf.py
│   │   │   │   ├── build_price_table.py
│   │   │   │   ├── db_config.py
│   │   │   │   ├── market_data_models.py
│   │   │   │   ├── prophit_alts_models.py
│   │   │   │   ├── pull_fmp_data.py
│   │   │   │   ├── schema.json
│   │   │   │   └── user_data_models.py
│   │   │   ├── jobs/
│   │   │   │   ├── fundamental_data.py
│   │   │   │   ├── price_table.py
│   │   │   │   └── ticker_table.py
│   │   │   └── monitor/
│   │   │       ├── health_check.py
│   │   │       └── query_performance_check.py
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
│   │   │       ├── phase_two_extract_assets_classes.py
│   │   │       ├── phase_two_filters.py
│   │   │       ├── phase_two_performance_metrics.py
│   │   │       ├── phase_two_prompts.py
│   │   │       ├── phase_two_run_llm.py
│   │   │       └── phase_two_run.py
│   │   ├── prophit_alts/
│   │   │   └── consumer_staples_fund/
│   │   │       ├── build_portfolio/
│   │   │       │   ├── cio/
│   │   │       │   │   ├── cio_agent.py
│   │   │       │   │   ├── cio_tool_registry.py
│   │   │       │   │   └── cio_tools.py
│   │   │       │   ├── cro/
│   │   │       │   │   ├── cro_agent.py
│   │   │       │   │   ├── cro_tool_registry.py
│   │   │       │   │   └── cro_tools.py
│   │   │       │   ├── industry_agents.py
│   │   │       │   ├── macro_agent.py
│   │   │       │   └── prompts/
│   │   │       │       ├── cio_agent_prompts.py
│   │   │       │       ├── cro_agent_prompts.py
│   │   │       │       ├── industry_prompts/
│   │   │       │       │   ├── beverages.py
│   │   │       │       │   ├── distribution_and_retail.py
│   │   │       │       │   ├── food_products.py
│   │   │       │       │   ├── household_products.py
│   │   │       │       │   ├── personal_care_products.py
│   │   │       │       │   └── tobacco.py
│   │   │       │       └── macro_agent_prompts.py
│   │   │       └── manage_portfolio/
│   │   │           └── drawdown_management.py
│   │   ├── prophit_gpt/
│   │   │   ├── gpt.py
│   │   │   ├── dataRetrievalTools/
│   │   │   │   ├── __init__.py
│   │   │   │   └── retrieve_financial_metrics.py
│   │   │   ├── functionSchemas/
│   │   │   │   └── tools.py
│   │   │   └── placeOrders/
│   │   │       ├── exitPosition.py
│   │   │       └── longOrder.py
│   │   ├── repositories/
│   │   │   ├── portfolio_data.py
│   │   │   ├── price_data.py
│   │   │   ├── prophit_alts_data.py
│   │   │   └── user_data.py
│   │   ├── services/
│   │   │   └── prophit_alts_service.py
│   │   ├── stress_test/
│   │   │   ├── engine.py
│   │   │   ├── pairwise_corr_analysis.py
│   │   │   ├── performance_analysis.py
│   │   │   ├── runner.py
│   │   │   └── scenarios.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── choose_model_and_client.py
│   │       ├── database.py
│   │       ├── determine_etf.py
│   │       ├── file_utils.py
│   │       ├── formatting.py
│   │       ├── ib_utils.py
│   │       ├── logging_config.py
│   │       ├── parsing_utils.py
│   │       ├── serialize_output.py
│   │       ├── ticker_utils.py
│   │       ├── token_count.py
│   │       └── validation_utils.py
│   └── testing/
│       ├── alpaca_trade.py
│       ├── calculations_vtwo_smoke_test.py
│       ├── cluster_analysis.py
│       ├── hedge_fund_stuff/
│       │   ├── Hedge_fund_portfolio_construction.py
│       │   └── Hedge_fund_risk_management.py
│       └── retail-fund-code.py
├── file_structure.md
├── git_helper.md
├── new_stucture.md
├── planning/
│   ├── calculations_folder_fix.md
│   ├── error_fixer.md
│   └── todo.md
├── README.md
├── requirements.txt
└── roadmap.md
