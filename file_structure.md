├── app/
│   ├── api/
│   │   ├── controller/
│   │   │   ├── prophit_alts_controller.py
│   │   │   └── user_controller.py
│   │   ├── prophit_alts.py
│   │   ├── response_envelope.py
│   │   ├── routes/
│   │   │   ├── agent_runs_router.py
│   │   │   ├── prophit_alts_router.py
│   │   │   ├── user_routes.py
│   │   │   └── websocket_router.py
│   │   ├── testing/
│   │   │   ├── prophit_alts_testing.py
│   │   │   ├── static/
│   │   │   │   └── test.html
│   │   │   └── user_testing.py
│   │   ├── user.py
│   │   └── websocket.py
│   ├── core/
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
│   │   │   │   │   ├── domain_memory.py
│   │   │   │   │   ├── episodic_memory.py
│   │   │   │   │   ├── error_memory.py
│   │   │   │   │   └── memory_store/
│   │   │   │   │       ├── domain_memory/
│   │   │   │   │       │   ├── beverages_memory.json
│   │   │   │   │       │   ├── cio_memory.json
│   │   │   │   │       │   ├── consumer_staples_distribution_and_retail_memory.json
│   │   │   │   │       │   ├── cro_memory.json
│   │   │   │   │       │   ├── food_products_memory.json
│   │   │   │   │       │   ├── household_products_memory.json
│   │   │   │   │       │   ├── optimizer_memory.json
│   │   │   │   │       │   ├── personal_care_products_memory.json
│   │   │   │   │       │   └── tobacco_memory.json
│   │   │   │   │       ├── episodic_memory.json
│   │   │   │   │       └── tool_error_memory.json
│   │   │   │   ├── tasks/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── execution_engine.py
│   │   │   │   │   ├── manager.py
│   │   │   │   │   ├── models.py
│   │   │   │   │   └── validator.py
│   │   │   │   └── tool_registry.py
│   │   │   └── tool_lib/
│   │   │       ├── agent_specific_tools/
│   │   │       │   ├── cio.py
│   │   │       │   ├── cro.py
│   │   │       │   └── industry.py
│   │   │       ├── base_tools/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── calculator.py
│   │   │       │   ├── planning_tool.py
│   │   │       │   └── search_engine_tool.py
│   │   │       ├── data_tools/
│   │   │       │   ├── industry_factors.py
│   │   │       │   ├── repository.py
│   │   │       │   ├── stock_screener.py
│   │   │       │   ├── sub_industry_factors.py
│   │   │       │   └── ticker_fundamentals.py
│   │   │       ├── portfolio_tools/
│   │   │       │   ├── beta.py
│   │   │       │   ├── builder.py
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
│   │   │       │   ├── stress_test.py
│   │   │       │   └── vol_es.py
│   │   │       └── ticker_tools/
│   │   │           ├── factors.py
│   │   │           ├── performance.py
│   │   │           └── weekly_returns.py
│   │   └── calculations/
│   │       ├── __init__.py
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
│   │       │   ├── __init__.py
│   │       │   ├── build/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── builder.py
│   │       │   │   └── optimizer.py
│   │       │   ├── concentration.py
│   │       │   ├── correlation.py
│   │       │   ├── factor_tilt.py
│   │       │   └── utils.py
│   │       ├── returns/
│   │       │   ├── __init__.py
│   │       │   └── calculator.py
│   │       ├── risk/
│   │       │   ├── __init__.py
│   │       │   └── calculator.py
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
│   │       └── technical/
│   │           ├── __init__.py
│   │           └── indicators.py
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
│   ├── domain/
│   │   ├── portfolio_operations/
│   │   │   ├── builder/
│   │   │   │   └── main.py
│   │   │   └── optimization/
│   │   │       ├── optimizer/
│   │   │       │   ├── agent.py
│   │   │       │   ├── prompts.py
│   │   │       │   └── tool_registry.py
│   │   │       └── user_data.py
│   │   ├── prophit_alts/
│   │   │   ├── consumer_staples_fund/
│   │   │   │   ├── build_portfolio/
│   │   │   │   │   ├── cio/
│   │   │   │   │   │   ├── agent.py
│   │   │   │   │   │   ├── prompts.py
│   │   │   │   │   │   └── tool_registry.py
│   │   │   │   │   ├── cro/
│   │   │   │   │   │   ├── agent.py
│   │   │   │   │   │   ├── portfolio_revisions.json
│   │   │   │   │   │   ├── prompts.py
│   │   │   │   │   │   └── tool_registry.py
│   │   │   │   │   ├── final_portfolio/
│   │   │   │   │   │   ├── cio.py
│   │   │   │   │   │   └── prompts.py
│   │   │   │   │   └── industry_agents/
│   │   │   │   │       ├── agents.py
│   │   │   │   │       ├── prompts.py
│   │   │   │   │       └── tool_registry.py
│   │   │   │   └── manage_portfolio/
│   │   │   │       └── drawdown_management.py
│   │   │   └── tech_ai_fund/
│   │   └── prophit_gpt/
│   │       └── main.py
│   ├── models/
│   │   ├── performance_models.py
│   │   ├── phase_two_models.py
│   │   ├── portfolio_models.py
│   │   └── style_factors_models.py
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
│   ├── services/
│   │   ├── agent_runs.py
│   │   ├── prophit_alts_service.py
│   │   └── websocket_manager_service.py
│   └── utils/
│       ├── __init__.py
│       ├── choose_model_and_client.py
│       ├── decorators/
│       │   ├── database.py
│       │   ├── price_data.py
│       │   └── timer.py
│       ├── gpt_parser.py
│       ├── logging_config.py
│       ├── serialize_output.py
│       ├── ticker_utils.py
│       ├── token_count.py
│       └── validation_utils.py
├── planning/
│   ├── error_fixer.md
│   ├── structure_migration.md
│   └── todo.md
├── tests/
│   ├── alpaca_trade.py
│   ├── calculations_vtwo_smoke_test.py
│   ├── cluster_analysis.py
│   ├── hedge_fund_stuff/
│   │   ├── Hedge_fund_portfolio_construction.py
│   │   └── Hedge_fund_risk_management.py
│   ├── portfolio_allocation.py
│   ├── retail-fund-code.py
│   ├── streaming_data.py
│   └── vector_storage/
│       ├── build.py
│       ├── corpus.faiss
│       ├── corpus.txt
│       ├── docs.jsonl
│       ├── embeddings.npy
│       ├── INDEX.yml
│       └── query.py
├── file_structure.md
├── main.py
├── output.json
├── README.md
├── requirements.txt
├── roadmap.md
├── t.py
└── tester.py


