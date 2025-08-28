ProphitAI/
├── backend/
│   ├── src/
│   │   ├── api/                           # API Layer (minimal changes)
│   │   │   ├── routes/                    # EXISTING - Route definitions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_routes.py        # Move auth routes here
│   │   │   │   ├── user_routes.py        # EXISTING
│   │   │   │   └── prophit_alts_router.py # EXISTING
│   │   │   │
│   │   │   ├── controllers/               # EXISTING - Keep your pattern
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_controller.py
│   │   │   │   └── prophit_alts_controller.py
│   │   │   │
│   │   │   └── middleware/                # NEW - Just the essentials
│   │   │       ├── __init__.py
│   │   │       └── error_handler.py      # Global error handling
│   │   │
│   │   ├── services/                      # NEW - Simple service layer
│   │   │   ├── __init__.py
│   │   │   ├── portfolio_service.py      # Orchestrates portfolio operations
│   │   │   ├── prophit_alts_service.py   # Orchestrates fund operations
│   │   │   └── calculation_service.py    # Orchestrates calculations
│   │   │
│   │   ├── repositories/                  # EXISTING - Just organize better
│   │   │   ├── __init__.py
│   │   │   ├── portfolio_data.py         # EXISTING
│   │   │   ├── price_data.py             # EXISTING
│   │   │   ├── prophit_alts_data.py      # EXISTING
│   │   │   └── user_data.py              # EXISTING
│   │   │
│   │   ├── models/                        # RENAME from data_models
│   │   │   ├── __init__.py
│   │   │   ├── performance_models.py     # EXISTING
│   │   │   ├── phase_two_models.py       # EXISTING
│   │   │   └── style_factors_models.py   # EXISTING
│   │   │
│   │   ├── domain/                        # Business logic (keep structure)
│   │   │   ├── portfolio_optimization/    # MOVE from src/
│   │   │   ├── calculations/              # MOVE from src/
│   │   │   ├── prophit_alts/              # MOVE from src/
│   │   │   ├── prophit_gpt/               # MOVE from src/
│   │   │   ├── analysts/                  # MOVE from src/
│   │   │   └── stress_test/               # MOVE from src/
│   │   │
│   │   ├── auth/                          # EXISTING - Keep as is
│   │   ├── db/                            # EXISTING - Keep as is
│   │   ├── utils/                         # EXISTING - Keep as is
│   │   ├── agentic_framework/             # EXISTING - Keep as is
│   │   └── config/                        # NEW - Simple config
│   │       ├── __init__.py
│   │       └── settings.py                # Centralized settings
│   │
│   ├── tests/                             # MOVE from src/api/testing
│   │   ├── __init__.py
│   │   ├── test_api/
│   │   └── test_services