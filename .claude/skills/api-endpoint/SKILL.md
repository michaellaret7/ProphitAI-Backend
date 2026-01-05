---
name: api-endpoint
description: Build complete FastAPI endpoints for ProphitAI following the layered architecture. Use when creating new API endpoints, routes, controllers, or services. Covers Router → Controller → Service → Repository pattern with caching and error handling.
---

## Overview

Build API endpoints following ProphitAI's 4-layer architecture with standardized response envelopes, error handling, and caching patterns.

## Architecture Flow

```
Request → Router → Controller → Service → Repository → Database
                       ↓
                 Response Envelope (ok_envelope)
```

## Quick Start: Creating a New Endpoint

### 1. Create Pydantic Models (in router file)

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict

class CreateResourceRequest(BaseModel):
    resourceName: str  # camelCase for API
    items: List[ItemModel]
    value: Optional[float] = Field(default=None, description="Description here")

    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError("Items cannot be empty")
        return v
```

### 2. Create Router (`app/api/routes/<domain>_router.py`)

```python
from fastapi import APIRouter, Query, Depends, Path, HTTPException
from pydantic import BaseModel
from app.api.controller.<domain> import my_controller
from app.api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["Domain Name"])

@router.post("/resources", status_code=201)
async def create_resource(
    body: CreateResourceRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Endpoint docstring shown in Swagger."""
    return await create_resource_controller(
        user_id=user_id,
        resource_name=body.resourceName,  # Convert camelCase → snake_case
        items=[i.model_dump() for i in body.items],
    )
```

### 3. Create Controller (`app/api/controller/<domain>.py`)

```python
from typing import Dict, Any
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.<domain>.<service> import MyService

@handle_controller_errors
async def create_resource_controller(
    *,
    user_id: str,
    resource_name: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Controller docstring.

    Cache TTL: 1 hour (3600s)
    """
    # For read operations: check cache first
    cache_key = f"resource:{user_id}:{resource_name}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Call service layer
    service = MyService()
    data = service.create_resource(
        user_id=user_id,
        resource_name=resource_name,
        items=items,
    )

    # Build response envelope
    response = ok_envelope(
        message="Resource created successfully",
        kind="domain#resource",
        resource_id=data.get("id"),
        self_link=f"/api/resources/{data.get('id')}",
        payload=data,
        status=201,
    )

    # Cache response (for read operations)
    await cache.set(cache_key, response, ttl=3600)

    # Invalidate related cache on mutations
    await cache.clear_pattern(f"user:resources:{user_id}:*")

    return response
```

### 4. Create Service (`app/services/<domain>/<service>.py`)

```python
from typing import Dict, Any, List

class MyService:
    """Service for domain operations."""

    def create_resource(
        self,
        *,
        user_id: str,
        resource_name: str,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Validation (raises ValueError for bad input)
        if not resource_name:
            raise ValueError("Resource name is required")
        if not items:
            raise ValueError("Items list cannot be empty")

        # Business logic
        processed_items = self._process_items(items)

        # Call repository
        result = create_resource_in_db(
            user_id=user_id,
            name=resource_name,
            items=processed_items,
        )

        return self._format_response(result)

    def _process_items(self, items: List[Dict]) -> List[Dict]:
        """Internal helper for item processing."""
        return [self._transform_item(i) for i in items]
```

### 5. Register Router (`main.py`)

```python
from app.api.routes.<domain>_router import router as domain_router

# Choose appropriate auth level:
# User-specific routes (require JWT + API key)
app.include_router(domain_router, prefix="/api", dependencies=auth_dependencies)

# Public data routes (API key only)
app.include_router(domain_router, prefix="/api", dependencies=api_key_only)

# No auth (webhooks, WebSocket)
app.include_router(domain_router, prefix="/api")
```

## Response Envelope

All responses use `ok_envelope()` for consistency:

```python
from app.api.response_envelope import ok_envelope

ok_envelope(
    message="Success message",
    kind="domain#resourceType",  # e.g., "users#portfolios", "portfolio#returns"
    resource_id="uuid-string",
    self_link="/api/path/to/resource",
    updated="2025-01-15T00:00:00Z",  # RFC3339 timestamp (optional)
    counts={
        'currentItemCount': 10,
        'itemsPerPage': 10,
        'startIndex': 1,
        'totalItems': 100,
    },
    payload=data,  # Dict or List
    status=200,  # HTTP status code
)
```

**Response Structure:**
```json
{
  "status": 200,
  "data": {
    "kind": "domain#resource",
    "id": "resource-id",
    "selfLink": "/api/resources/id",
    "payload": { ... }
  },
  "message": "Success message"
}
```

## Error Handling

The `@handle_controller_errors` decorator handles all exceptions:

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `ValueError` | 400 Bad Request | Validation errors in service layer |
| `HTTPException` | Pass through | Specific HTTP errors (404, 403, etc.) |
| Other exceptions | 500 Internal Server Error | Unexpected errors |

**Usage:**
```python
# In service layer - raise ValueError for validation
if not valid_input:
    raise ValueError("Input validation failed: reason")

# In controller - raise HTTPException for access control
if not user_owns_resource:
    raise HTTPException(status_code=403, detail="Access denied")

if not resource_found:
    raise HTTPException(status_code=404, detail="Resource not found")
```

## Caching Strategy

**Common TTLs:**
| Data Type | TTL | Seconds |
|-----------|-----|---------|
| Static data (sectors, industries) | 1 day | 86400 |
| Performance/analytics data | 1 day | 86400 |
| Fund data | 1 hour | 3600 |
| Factor analysis | 6 hours | 21600 |

**Cache Patterns:**
```python
# Read: Check cache first
cache_key = f"domain:resource:{id}:{params}"
cached = await cache.get(cache_key)
if cached:
    return cached

# Compute and cache
data = service.compute()
response = ok_envelope(...)
await cache.set(cache_key, response, ttl=3600)

# Write: Invalidate related cache
await cache.clear_pattern(f"domain:resource:{id}:*")
```

## Authentication

**Three auth levels in main.py:**

```python
# 1. Full auth (user-specific routes)
auth_dependencies = [Depends(validate_api_key), Depends(clerk_auth)]

# 2. API key only (public data routes)
api_key_only = [Depends(validate_api_key)]

# 3. No auth (webhooks, WebSocket)
# Just include router without dependencies
```

**Get user ID from Clerk:**
```python
from app.api.auth.clerk import get_clerk_user_id

async def get_user_id_from_clerk(clerk_id: str = Depends(get_clerk_user_id)) -> str:
    """Get internal database user_id from Clerk ID."""
    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data.get("id")
```

## Best Practices

**DO:**
- Use `@handle_controller_errors` on ALL controllers
- Implement caching for read operations
- Invalidate cache on mutations (create/update/delete)
- Use `ok_envelope()` for ALL responses
- Raise `ValueError` in services for validation errors
- Keep routers thin - delegate to controllers
- Use snake_case internally, camelCase for API
- Document cache keys and TTLs in controller docstrings
- Use keyword-only arguments (`*,`) in controller functions

**DON'T:**
- Put business logic in routers
- Put database queries in controllers
- Forget to invalidate cache on mutations
- Mix error handling patterns
- Create backwards compatibility layers
- Return raw data without envelope

## File Locations

| Layer | Location | Naming |
|-------|----------|--------|
| Router | `app/api/routes/<domain>_router.py` | `*_router.py` |
| Controller | `app/api/controller/<domain>.py` or `<domain>/<file>.py` | `*_controller` functions |
| Service | `app/services/<domain>/<service>.py` | `*Service` classes |
| Repository | `app/repositories/<domain>.py` | Functions with `@with_session` |
| Models | `app/db/core/models/<db>_models.py` | SQLAlchemy models |

## Reference

For detailed patterns and examples, see:
- `references/endpoint-examples.md` - Complete endpoint examples
- `app/api/routes/portfolio_router.py` - Full router implementation
- `app/api/controller/portfolio/` - Controller organization
- `app/api/response_envelope.py` - Response envelope implementation
