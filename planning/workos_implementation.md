## WorkOS code appearances in backend (for reset)

### backend/src/auth/config.py
```python
import os
from workos import WorkOSClient
from dotenv import load_dotenv

load_dotenv()

# Initialize WorkOS client
workos_client = WorkOSClient(
    api_key=os.environ["WORKOS_API_KEY"],
    client_id=os.environ["WORKOS_CLIENT_ID"]
)

# Configuration constants
REDIRECT_URI = os.environ["WORKOS_REDIRECT_URI"]

print(workos_client)
```

## Clean WorkOS backend re-implementation (actionable plan)

### Scope
- **SSO only (minimal)**: Login + callback, persist `workos_id`, redirect to frontend.
- Optional later: audit logs, webhooks, richer session management.

### TODO checklist
- [ ] Fix router import in `backend/main.py`
- [ ] Finalize `backend/src/auth/config.py` (remove debug print; envs only)
- [ ] Implement minimal SSO in `backend/src/auth/sso.py` (login + callback)
- [ ] Update `backend/src/repositories/user_data.py` to persist `workos_id`
- [ ] Smoke-test the flow locally

---

### 1) Router import (wire-up)
Change import to use the existing `sso.py` router.

```python
# File: backend/main.py
# Before
from backend.src.auth.routes import router as auth_router

# After
from backend.src.auth.sso import router as auth_router
```

`app.include_router(auth_router)` can remain as-is.

---

### 2) WorkOS client config (minimal, no side-effects)
Use env vars only; remove prints. Provide a sane default for local redirect.

```python
# File: backend/src/auth/config.py
import os
from workos import WorkOSClient
from dotenv import load_dotenv

load_dotenv()

workos_client = WorkOSClient(
    api_key=os.environ["WORKOS_API_KEY"],
    client_id=os.environ["WORKOS_CLIENT_ID"],
)

REDIRECT_URI = os.environ.get(
    "WORKOS_REDIRECT_URI", "http://localhost:8000/auth/callback"
)
```

Required env vars:
- `WORKOS_API_KEY`
- `WORKOS_CLIENT_ID`
- `WORKOS_REDIRECT_URI` (optional in dev; defaults to the callback above)

---

### 3) Minimal SSO endpoints (login + callback)
Keep it simple: generate URL, exchange code, upsert user, redirect to frontend.

```python
# File: backend/src/auth/sso.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from .config import workos_client, REDIRECT_URI
from backend.src.repositories.user_data import get_user_basic_info, add_user

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/login")
async def login():
    # TODO: replace with your org/connection lookup if needed
    organization_id = "org_test_idp"

    authorization_url = workos_client.sso.get_authorization_url(
        organization_id=organization_id,
        redirect_uri=REDIRECT_URI,
    )
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        profile_and_token = workos_client.sso.get_profile_and_token(code)
        profile = profile_and_token.profile

        # 1) Try to find user by email
        existing = get_user_basic_info(email=profile.email)

        # 2) Create if absent, otherwise ensure workos_id is persisted (see repo changes below)
        if not existing:
            add_user(
                email=profile.email,
                first_name=profile.first_name or "",
                last_name=profile.last_name or "",
                # new optional param you'll add
                workos_id=profile.id,
            )
        else:
            # If you add update helper, call it here to persist profile.id
            pass

        return RedirectResponse(url="http://localhost:5173/dashboard")
    except Exception:
        return RedirectResponse(url="/auth/login")
```

---

### 4) Repository changes (persist workos_id)
Make `add_user` accept an optional `workos_id` and add a tiny helper to update it when a user already exists.

```python
# File: backend/src/repositories/user_data.py
from typing import Optional

def add_user(email: str, first_name: str, last_name: str, workos_id: Optional[str] = None):
    session = UserSession()

    user = session.query(User).filter(User.email == email).first()
    if user:
        session.close()
        return user, "User already exists"

    user = User(
        id=uuid.uuid4(),
        workos_id=workos_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    session.commit()
    session.close()

def update_user_workos_id(email: str, workos_id: str) -> None:
    session = UserSession()
    user = session.query(User).filter(User.email == email).first()
    if user and user.workos_id != workos_id:
        user.workos_id = workos_id
        session.commit()
    session.close()
```

Then in `auth/sso.py` callback, call `update_user_workos_id(profile.email, profile.id)` when `existing` is found.

---

### 5) Smoke test
1. Start backend on port 8000.
2. Visit `http://localhost:8000/auth/login` and complete SSO.
3. Verify a user row is created/updated with `workos_id`.
4. Confirm redirect to `http://localhost:5173/dashboard`.

---

### Later (optional)
- Add CSRF `state` on login and verify on callback.
- Replace hardcoded `organization_id` with lookup by email domain/company.
- Implement real session/JWT and plug into `get_current_user` in `auth/dependencies.py`.
- Add WorkOS Audit Logs and Webhooks.

