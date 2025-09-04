ProphitAI/
├── app/                                # Main FastAPI application
│   ├── __init__.py
│   ├── main.py                         # FastAPI app initialization (move from backend/main.py)
│   ├── config.py                       # Environment & app configuration
│   │
│   ├── api/                            # API endpoints layer
│   │   ├── __init__.py
│   │   ├── v1/                         # API versioning
│   │   │   ├── __init__.py
│   │   │   ├── routes/                 # Route definitions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── users.py            # User endpoints
│   │   │   │   ├── portfolio.py        # Portfolio endpoints
│   │   │   │   └── prophit_alts.py     # Fund endpoints
│   │   │   └── api.py                  # Main router aggregator
│   │   └── dependencies.py             # Shared dependencies
│   │
│   ├── controllers/                     # Business logic handlers (EXISTING pattern)
│   │   ├── __init__.py
│   │   ├── user_controller.py          # Keep existing logic
│   │   ├── portfolio_controller.py
│   │   └── prophit_alts_controller.py  # Keep existing logic
│   │
│   ├── models/                         # Pydantic schemas (not DB models)
│   │   ├── __init__.py
│   │   ├── requests/                   # Request models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── portfolio.py
│   │   ├── responses/                  # Response models
│   │   │   ├── __init__.py
│   │   │   ├── envelope.py             # Response envelope pattern (EXISTING)
│   │   │   └── portfolio.py
│   │   └── domain/                     # Business domain models (from data_models/)
│   │       ├── __init__.py
│   │       ├── performance.py
│   │       ├── phase_two.py
│   │       └── style_factors.py
│   │
│   ├── core/                           # Core utilities
│   │   ├── __init__.py
│   │   ├── exceptions.py               # Custom exceptions
│   │   ├── logging.py                  # Logging config (from utils/)
│   │   └── security.py                 # Minimal auth if needed
│   │
│   └── middleware/                     # FastAPI middleware
│       ├── __init__.py
│       └── error_handler.py            # Global error handling
│
├── services/                           # Business service layer (EXISTING)
│   ├── __init__.py
│   └── prophit_alts_service.py        # Keep existing implementation
│
├── repositories/                       # Data access layer (EXISTING - just rename)
│   ├── __init__.py
│   ├── portfolio.py                   # Was portfolio_data.py
│   ├── price.py                       # Was price_data.py
│   ├── prophit_alts.py                # Was prophit_alts_data.py
│   └── user.py                        # Was user_data.py
│
├── db/                                 # Database layer (EXISTING - keep as is)
│   ├── __init__.py
│   ├── core/                           # Keep entire structure
│   │   ├── db_config.py
│   │   ├── market_data_models.py
│   │   ├── prophit_alts_models.py
│   │   ├── user_data_models.py
│   │   ├── pull_fmp_data.py
│   │   ├── schema.json
│   │   └── ...
│   ├── jobs/                           # Keep as is
│   └── monitor/                        # Keep as is
│
├── business_logic/                     # Domain-specific business modules
│   ├── __init__.py
│   ├── portfolio_optimization/        # Move from backend/src/
│   │   ├── phase_one/
│   │   ├── phase_two/
│   │   └── runner.py
│   ├── prophit_alts/                  # Move from backend/src/
│   │   └── consumer_staples_fund/
│   │       ├── build_portfolio/
│   │       └── manage_portfolio/
│   ├── prophit_gpt/                   # Move from backend/src/
│   │   ├── gpt.py
│   │   └── ...
│   └── stress_test/                   # Move from backend/src/
│       ├── engine.py
│       ├── scenarios.py
│       └── ...
│
├── calculations_v2/                    # KEEP AS IS - Your calculation engine
│   ├── __init__.py
│   ├── core/
│   ├── factors/
│   ├── performance/
│   ├── portfolio/
│   ├── returns/
│   ├── risk/
│   ├── sectors/
│   └── technical/
│
├── agentic_framework/                  # KEEP COMPLETELY SEPARATE - Don't touch
│   └── [keep entire existing structure]
│
├── utils/                              # General utilities (EXISTING - simplified)
│   ├── __init__.py
│   ├── formatting.py
│   ├── validation.py                  # Was validation_utils.py
│   ├── serialize.py                   # Was serialize_output.py
│   ├── parsers.py                     # Was parsing_utils.py
│   ├── ticker.py                      # Was ticker_utils.py
│   ├── file.py                        # Was file_utils.py
│   └── model_selector.py              # Was choose_model_and_client.py
│
├── tests/                              # Move from backend/testing
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── unit/
│   ├── integration/
│   └── smoke/
│       └── calculations_smoke_test.py
│
├── scripts/                            # Utility scripts
│   ├── __init__.py
│   └── migrate_data.py
│
├── main.py                             # Entry point: uvicorn app.main:app
├── requirements.txt
├── .env.example
└── README.md