# Backend Structure Migration Plan

## Overview
This document outlines the migration from the current `backend/src/` structure to a cleaner `app/` structure.

## Target Structure

```
ProphitAI/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── controllers/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   │   ├── requests/
│   │   ├── responses/
│   │   └── domain/
│   ├── domain/
│   │   ├── portfolio_optimization/
│   │   ├── prophit_alts/
│   │   ├── prophit_gpt/
│   │   └── stress_test/
│   ├── db/
│   │   ├── core/
│   │   ├── jobs/
│   │   └── monitor/
│   ├── core/
│   ├── utils/
│   ├── middleware/
│   └── core_libs/
│       ├── calculations/
│       └── agent_framework/
├── tests/
├── scripts/
└── main.py
```

## Migration Steps

### Phase 1: Setup New Structure (No Code Changes)
1. Create the new directory structure
   ```bash
   mkdir -p app/{api,services,repositories,models,domain,db,core,utils,middleware,core_libs}
   mkdir -p app/api/{routes,controllers}
   mkdir -p app/models/{requests,responses,domain}
   mkdir -p app/core_libs/{calculations,agent_framework}
   mkdir -p tests/{unit,integration,smoke}
   mkdir -p scripts
   ```

### Phase 2: Move Core Libraries
1. **Move calculations_v2 → app/core_libs/calculations/**
   ```bash
   mv backend/src/calculations_v2/* app/core_libs/calculations/
   ```

2. **Move agentic_framework → app/core_libs/agent_framework/**
   ```bash
   mv backend/src/agentic_framework/* app/core_libs/agent_framework/
   ```

### Phase 3: Move API Layer
1. **Routes**
   - `backend/src/api/routes/*.py` → `app/api/routes/`
   - Rename files for clarity:
     - `user_routes.py` → `users.py`
     - `prophit_alts_router.py` → `prophit_alts.py`

2. **Controllers**
   - `backend/src/api/controller/*.py` → `app/api/controllers/`

3. **Response Models**
   - `backend/src/api/response_envelope.py` → `app/models/responses/envelope.py`

4. **Dependencies**
   - `backend/src/auth/dependencies.py` → `app/api/dependencies.py`

### Phase 4: Move Data Layer
1. **Repositories**
   - `backend/src/repositories/*.py` → `app/repositories/`
   - Rename for consistency:
     - `portfolio_data.py` → `portfolio.py`
     - `price_data.py` → `price.py`
     - `prophit_alts_data.py` → `prophit_alts.py`
     - `user_data.py` → `user.py`

2. **Database**
   - `backend/src/db/*` → `app/db/`
   - Keep entire structure as-is

3. **Models**
   - `backend/src/data_models/*.py` → `app/models/domain/`

### Phase 5: Move Business Logic
1. **Services**
   - `backend/src/services/*.py` → `app/services/`

2. **Domain Logic**
   - `backend/src/portfolio_optimization/` → `app/domain/portfolio_optimization/`
   - `backend/src/prophit_alts/` → `app/domain/prophit_alts/`
   - `backend/src/prophit_gpt/` → `app/domain/prophit_gpt/`
   - `backend/src/stress_test/` → `app/domain/stress_test/`

### Phase 6: Move Utilities
1. **Utils**
   - `backend/src/utils/*.py` → `app/utils/`
   - Rename for clarity:
     - `validation_utils.py` → `validation.py`
     - `serialize_output.py` → `serialize.py`
     - `parsing_utils.py` → `parsers.py`
     - `ticker_utils.py` → `ticker.py`
     - `file_utils.py` → `file.py`
     - `choose_model_and_client.py` → `model_selector.py`

2. **Core Utilities**
   - `backend/src/utils/logging_config.py` → `app/core/logging.py`
   - Create `app/core/exceptions.py` for custom exceptions
   - Create `app/core/security.py` for minimal auth utilities

### Phase 7: Move Tests
1. **Test Files**
   - `backend/testing/*.py` → `tests/`
   - `backend/src/api/testing/*.py` → `tests/api/`
   - Organize by type: unit/, integration/, smoke/

### Phase 8: Update Entry Point
1. **Main Application**
   - `backend/main.py` → `app/main.py`
   - Create new `main.py` at root:
   ```python
   # main.py
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
   ```

## Import Updates Required

### Old Import Pattern
```python
from backend.src.repositories.portfolio_data import get_portfolio
from backend.src.calculations_v2.factors.growth import GrowthCalculator
from backend.src.agentic_framework.base_agent import BaseAgent
```

### New Import Pattern
```python
from app.repositories.portfolio import get_portfolio
from app.core_libs.calculations.factors.growth import GrowthCalculator
from app.core_libs.agent_framework.base_agent import BaseAgent
```

## Update Script
Create a script to automatically update imports:

```python
# scripts/update_imports.py
import os
import re

IMPORT_MAPPINGS = {
    r'from backend\.src\.repositories\.portfolio_data': 'from app.repositories.portfolio',
    r'from backend\.src\.repositories\.price_data': 'from app.repositories.price',
    r'from backend\.src\.repositories\.user_data': 'from app.repositories.user',
    r'from backend\.src\.repositories\.prophit_alts_data': 'from app.repositories.prophit_alts',
    r'from backend\.src\.calculations_v2': 'from app.core_libs.calculations',
    r'from backend\.src\.agentic_framework': 'from app.core_libs.agent_framework',
    r'from backend\.src\.api\.response_envelope': 'from app.models.responses.envelope',
    r'from backend\.src\.api\.controller': 'from app.api.controllers',
    r'from backend\.src\.api\.routes': 'from app.api.routes',
    r'from backend\.src\.services': 'from app.services',
    r'from backend\.src\.db': 'from app.db',
    r'from backend\.src\.utils': 'from app.utils',
    r'from backend\.src\.portfolio_optimization': 'from app.domain.portfolio_optimization',
    r'from backend\.src\.prophit_alts': 'from app.domain.prophit_alts',
    r'from backend\.src\.prophit_gpt': 'from app.domain.prophit_gpt',
    r'from backend\.src\.stress_test': 'from app.domain.stress_test',
    r'from backend\.src\.data_models': 'from app.models.domain',
    r'from backend\.src\.auth\.dependencies': 'from app.api.dependencies',
}

def update_imports_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old_pattern, new_pattern in IMPORT_MAPPINGS.items():
        content = re.sub(old_pattern, new_pattern, content)
    
    with open(filepath, 'w') as f:
        f.write(content)

def update_all_imports(root_dir='app'):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                update_imports_in_file(filepath)
                print(f"Updated: {filepath}")

if __name__ == "__main__":
    update_all_imports()
```

## Testing Strategy

### 1. Pre-Migration Tests
- Run all existing tests and document passing status
- Create smoke tests for critical paths

### 2. Post-Migration Validation
- **Import Test**: Verify all imports resolve correctly
- **API Test**: Ensure all endpoints respond
- **Database Test**: Confirm database connections work
- **Unit Tests**: Run all unit tests
- **Integration Tests**: Run integration test suite

### 3. Rollback Plan
- Keep backup of original `backend/` folder
- Document any configuration changes
- Maintain ability to revert if issues arise

## Cleanup Tasks

After successful migration:
1. Remove old `backend/` directory
2. Update `.gitignore` if needed
3. Update README.md with new structure
4. Update deployment scripts
5. Update CI/CD pipelines
6. Archive old structure documentation

## Success Criteria

- [ ] All tests pass
- [ ] API endpoints functional
- [ ] No import errors
- [ ] Database operations work
- [ ] Agent framework operational
- [ ] Calculations work correctly
- [ ] Documentation updated
- [ ] Team informed of changes