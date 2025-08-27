# Error: ImportError: cannot import name 'get_current_user' from 'backend.src.auth'

## Terminal output (excerpt)
```
ImportError: cannot import name 'get_current_user' from 'backend.src.auth' (/Users/michaellaret/Desktop/ProphitAI/backend/src/auth/__init__.py)
  at backend/src/api/portfolio.py:8
  and similar in backend/src/api/runner.py, backend/src/api/prophitgpt.py
```

## Diagnosis
- `backend/src/api/*` modules import `get_current_user` from the package `backend.src.auth`.
- `get_current_user` is defined in `backend/src/auth/dependencies.py` and is not exported in `backend/src/auth/__init__.py`.
- Therefore, importing from `backend.src.auth` fails.

## Files involved
- `backend/src/api/portfolio.py` (line 8)
- `backend/src/api/runner.py` (line 7)
- `backend/src/api/prophitgpt.py` (line 12)
- `backend/src/auth/dependencies.py` (source of the function)
- `backend/src/auth/__init__.py` (currently empty)

## Plan (simple, minimal change)
Recommended (single-line change, keeps existing imports working):
1) Re-export the dependency in `backend/src/auth/__init__.py`:
   - Add: `from .dependencies import get_current_user`

Alternative (explicit imports at call sites):
2) Update imports in the three API modules:
   - Change `from backend.src.auth import get_current_user` → `from backend.src.auth.dependencies import get_current_user` in:
     - `backend/src/api/portfolio.py`
     - `backend/src/api/runner.py`
     - `backend/src/api/prophitgpt.py`

## Request for approval
- Proceed with the recommended approach (1) to re-export via `__init__.py`?
  - This is the least-invasive fix and preserves existing import paths.
- Or prefer approach (2) to make imports explicit at call sites?

---

# Error: ModuleNotFoundError: No module named 'backend.jobs'

## Terminal output (excerpt)
```
ModuleNotFoundError: No module named 'backend.jobs'
  at backend/src/data/__init__.py:16
```

## Diagnosis
- `backend/src/data/__init__.py` performs a package-level import:
  ```python
  from backend.jobs.update_database_schema import (
      recreate_database_schemas
  )
  ```
- There is no `backend/jobs/update_database_schema.py` in the repo. The closest directory is `backend/db/jobs/`, and there is no `update_database_schema.py` file anywhere.
- This import runs whenever `backend.src.data` is imported (e.g., by `portfolio_optimization`), causing the crash.
- `recreate_database_schemas` is not referenced anywhere else in the codebase.

## Plan (simple, minimal change)
1) Remove the invalid import from `backend/src/data/__init__.py` to eliminate the side-effect and unblock app startup.
   - Delete the block:
     ```python
     from backend.jobs.update_database_schema import (
         recreate_database_schemas
     )
     ```
2) If schema recreation is needed later, add a proper module under the correct path and call it explicitly from a CLI/script, not at package import time.

## Request for approval
- Proceed with step (1) and remove the invalid import from `backend/src/data/__init__.py`?


