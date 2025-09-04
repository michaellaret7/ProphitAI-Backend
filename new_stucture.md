ProphitAI/
├── src/
│   ├── api/                           # API Layer (minimal changes)
│   │   ├── routes/                    # EXISTING - Route definitions
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py        # Move auth routes here
│   │   │   ├── user_routes.py        # EXISTING
│   │   │   └── prophit_alts_router.py # EXISTING
│   │   │
│   │   ├── controllers/               # EXISTING - Keep your pattern
│   │   │   ├── __init__.py
│   │   │   ├── user_controller.py
│   │   │   └── prophit_alts_controller.py
│   │   │
│   │   └── middleware/                # NEW - Just the essentials
│   │       ├── __init__.py
│   │       └── error_handler.py      # Global error handling
│   │
│   ├── services/                      # NEW - Simple service layer
│   │   ├── __init__.py
│   │   ├── portfolio_service.py      # Orchestrates portfolio operations
│   │   ├── prophit_alts_service.py   # Orchestrates fund operations
│   │   └── calculation_service.py    # Orchestrates calculations
│   │
│   ├── repositories/                  # EXISTING - Just organize better
│   │   ├── __init__.py
│   │   ├── portfolio_data.py         # EXISTING
│   │   ├── price_data.py             # EXISTING
│   │   ├── prophit_alts_data.py      # EXISTING
│   │   └── user_data.py              # EXISTING
│   │
│   ├── models/                        # RENAME from data_models
│   │   ├── __init__.py
│   │   ├── performance_models.py     # EXISTING
│   │   ├── phase_two_models.py       # EXISTING
│   │   └── style_factors_models.py   # EXISTING
│   │
│   ├── business/                        # Business logic (keep structure)
│   │   ├── portfolio_optimization/    # MOVE from src/
│   │   ├── calculations/              # MOVE from src/
│   │   ├── prophit_alts/              # MOVE from src/
│   │   ├── prophit_gpt/               # MOVE from src/
│   │   ├── analysts/                  # MOVE from src/
│   │   └── stress_test/               # MOVE from src/
│   │
│   ├── auth/                          # EXISTING - Keep as is
│   ├── db/                            # EXISTING - Keep as is
│   ├── utils/                         # EXISTING - Keep as is
│   ├── agentic_framework/             # EXISTING - Keep as is
│   └── config/                        # NEW - Simple config
│       ├── __init__.py
│       └── settings.py                # Centralized settings
│
├── tests/                             # MOVE from src/api/testing
│   ├── __init__.py
│   ├── test_api/
│   └── test_services



ProphitAI/
├── app/                                          
│   ├── main.py                                   # from backend/main.py (FastAPI app + router includes)
│   ├── config.py                                 # from backend/src/auth/config.py
│   │
│   ├── routes/
│   │   ├── auth_routes.py                        # from backend/src/auth/sso.py
│   │   ├── user_routes.py                        # from backend/src/api/routes/user_routes.py
│   │   ├── prophit_alts_routes.py                # from backend/src/api/routes/prophit_alts_router.py (rename)
│   │   ├── user.py                               # from backend/src/api/user.py (router aggregator; optional later removal)
│   │   └── prophit_alts.py                       # from backend/src/api/prophit_alts.py (router aggregator; optional later removal)
│   │
│   ├── controllers/
│   │   ├── user_controller.py                    # from backend/src/api/controller/user_controller.py
│   │   └── prophit_alts_controller.py            # from backend/src/api/controller/prophit_alts_controller.py
│   │
│   ├── services/
│   │   ├── prophit_alts_service.py               # from backend/src/services/prophit_alts_service.py
│   │   ├── prophit_gpt/                          # from backend/src/prophit_gpt/
│   │   │   ├── gpt.py
│   │   │   ├── dataRetrievalTools/
│   │   │   ├── functionSchemas/
│   │   │   └── placeOrders/
│   │   ├── calculations/                         # from backend/src/calculations/
│   │   ├── portfolio_optimization/               # from backend/src/portfolio_optimization/
│   │   ├── stress_test/                          # from backend/src/stress_test/
│   │   ├── analysts/                             # from backend/src/analysts/
│   │   ├── prophit_alts/                         # from backend/src/prophit_alts/
│   │   └── agentic_framework/                    # from backend/src/agentic_framework/
│   │
│   ├── repositories/
│   │   ├── portfolio_data.py                     # from backend/src/repositories/portfolio_data.py
│   │   ├── price_data.py                         # from backend/src/repositories/price_data.py
│   │   ├── prophit_alts_data.py                  # from backend/src/repositories/prophit_alts_data.py
│   │   └── user_data.py                          # from backend/src/repositories/user_data.py
│   │
│   ├── models/
│   │   ├── db/
│   │   │   ├── market_data_models.py             # from backend/src/db/core/market_data_models.py
│   │   │   ├── user_data_models.py               # from backend/src/db/core/user_data_models.py
│   │   │   ├── prophit_alts_models.py            # from backend/src/db/core/prophit_alts_models.py
│   │   │   └── db_config.py                      # from backend/src/db/core/db_config.py
│   │   └── data_models/                          # from backend/src/data_models/
│   │
│   ├── schemas/
│   │   ├── auth_schemas.py                       # from backend/src/auth/models.py (rename)
│   │   └── response_envelope.py                  # from backend/src/api/response_envelope.py
│   │
│   ├── middleware/
│   │   ├── auth_middleware.py                    # from backend/src/auth/dependencies.py (rename)
│   │   └── audit.py                              # from backend/src/auth/audit.py (empty file retained)
│   │
│   ├── utils/
│   │   ├── choose_model_and_client.py
│   │   ├── database.py
│   │   ├── determine_etf.py
│   │   ├── file_utils.py
│   │   ├── formatting.py
│   │   ├── ib_utils.py
│   │   ├── logging_config.py
│   │   ├── parsing_utils.py
│   │   ├── serialize_output.py
│   │   ├── ticker_utils.py
│   │   ├── token_count.py
│   │   └── validation_utils.py
│   │
│   └── data/
│       └── user_information.py                   # from backend/src/data/user_information.py
│
├── migrations/
│   ├── schema.json                               # from backend/src/db/core/schema.json
│
├── scripts/
│   ├── db/
│   │   ├── build_etf_data.py                     # from backend/src/db/core/build_etf_data.py
│   │   ├── build_price_table.py                  # from backend/src/db/core/build_price_table.py
│   │   ├── pull_fmp_data.py                      # from backend/src/db/core/pull_fmp_data.py
│   │   └── jobs/                                 # from backend/src/db/jobs/
│   │       ├── fundamental_data.py
│   │       ├── price_table.py
│   │       └── ticker_table.py
│   ├── monitor/                                  # from backend/src/db/monitor/
│   │   ├── health_check.py
│   │   └── query_performance_check.py
│   └── api/
│       └── runner.py                             # from backend/src/api/runner.py
│
├── tests/
│   ├── test_users.py                             # from backend/src/api/testing/user_testing.py (rename)
│   └── test_prophit_alts.py                      # from backend/src/api/testing/prophit_alts_testing.py (rename)
│
├── logs/                                         # (add, not committed)
├── uploads/                                      # (add, not committed)
├── run.py                                        # from backend/main.py (alternative placement if preferred)
├── README.md
├── requirements.txt
├── requirements-dev.txt                          # (add)
├── .env                                          # (add)
├── .env.example                                  # (add)
├── .gitignore                                    # (add)
├── roadmap.md
└── file_structure.md