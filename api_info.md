## **ProphitAI API Architecture Overview**

### **Layered Architecture**

The API follows a clean, layered architecture with clear separation of concerns:

```
Request Flow:
Client → Router → Controller → Service → Repository → Database
                     ↓
                 Response Envelope
```

---

### **1. Router Layer** (`app/api/routes/`)

**Purpose:** Define HTTP endpoints, request/response models, and route parameters

**Pattern:**
- Use Pydantic models for request/response validation
- Define route handlers with FastAPI decorators
- Convert camelCase (API) to snake_case (internal)
- Delegate business logic to controllers

**Example:** [portfolio_router.py](app/api/routes/portfolio_router.py:1-218)

```python
from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr

router = APIRouter()

class CreatePortfolioRequest(BaseModel):
    email: EmailStr
    companyName: str
    portfolioName: str
    positions: List[PositionModel]

@router.post("/portfolios", status_code=201)
async def create_portfolio(body: CreatePortfolioRequest):
    return await create_portfolio_controller(
        email=body.email,
        company_name=body.companyName,  # camelCase → snake_case
        portfolio_name=body.portfolioName,
        positions=[p.dict() for p in body.positions],
    )
```

---

### **2. Controller Layer** (`app/api/controller/`)

**Purpose:** Handle caching, error handling, and response formatting

**Pattern:**
- Decorated with `@handle_controller_errors` for standardized error handling
- Implement Redis caching with TTL strategies
- Call service layer for business logic
- Format responses using `ok_envelope()`
- Invalidate cache on mutations (create/update/delete)

**Example:** [portfolio.py](app/api/controller/portfolio.py:1-479)

```python
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors

@handle_controller_errors
async def get_portfolio_returns_controller(
    *,
    portfolio_id: str,
    years: int = 2,
) -> Dict[str, Any]:
    """Cache TTL: 1 day (86400s)"""

    # Generate cache key
    cache_key = f"portfolio:returns:{portfolio_id}:{years}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute data
    service = PortfolioReturnsService(portfolio_id=portfolio_id, years=years)
    returns_data = service.get_returns_series()

    # Build response envelope
    response = ok_envelope(
        message="Portfolio returns retrieved successfully",
        kind="portfolio#returns",
        resource_id=portfolio_id,
        self_link=f"/api/portfolio/returns?portfolioId={portfolio_id}",
        payload=returns_data,
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response
```

---

### **3. Service Layer** (`app/services/`)

**Purpose:** Implement domain business logic and data transformations

**Pattern:**
- Encapsulate domain logic in service classes
- Validate business rules
- Call repositories for data access
- Transform data for API consumption
- Raise `ValueError` for validation errors (caught by controller decorator)

**Example:** [portfolio.py](app/services/portfolio/portfolio.py:1-248)

```python
class PortfolioService:
    """Service for portfolio CRUD operations"""

    def create_portfolio(
        self,
        *,
        email: str,
        company_name: str,
        portfolio_name: str,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # Validate inputs
        if not email:
            raise ValueError("Email is required")
        if not positions or not isinstance(positions, list):
            raise ValueError("Positions must be a non-empty list")

        # Transform and persist
        position_objs = [Position(**p) for p in positions]
        add_portfolio(
            portfolio=position_objs,
            company_name=company_name,
            user_email=email,
            portfolio_name=portfolio_name,
        )

        # Return formatted data
        return self._get_portfolio_list_data(email)
```

---

### **4. Repository Layer** (`app/repositories/`)

**Purpose:** Data access and database operations

**Pattern:**
- Direct database queries (SQLAlchemy/Peewee)
- CRUD operations
- No business logic - just data access
- Returns raw database results

---

### **5. Response Envelope** ([response_envelope.py](app/api/response_envelope.py:1-78))

**Purpose:** Standardized API response format (Google JSON Style Guide)

**Structure:**
```python
{
  "status": 200,
  "data": {
    "kind": "resource#type",           # Resource identifier
    "id": "resource-id",                # Resource UUID
    "selfLink": "/api/resource/path",  # URL to resource
    "updated": "2025-01-15T00:00:00Z", # RFC3339 timestamp
    "currentItemCount": 10,             # Pagination metadata
    "itemsPerPage": 10,
    "startIndex": 1,
    "totalItems": 10,
    "payload": { /* actual data */ }    # The real data
  },
  "message": "Success message"
}
```

**Helper Function:**
```python
ok_envelope(
    message="Portfolio created successfully",
    kind="users#portfolios",
    resource_id=user_id,
    self_link=f"/api/user/portfolios?email={email}",
    counts={
        'currentItemCount': 3,
        'itemsPerPage': 3,
        'startIndex': 1,
        'totalItems': 3,
    },
    payload=portfolios_data,
    status=201,
)
```

---

### **6. Error Handling** ([api_decorators.py](app/utils/decorators/api_decorators.py:1-75))

**@handle_controller_errors Decorator:**
- Converts `ValueError` → 400 Bad Request
- Converts `HTTPException` → Pass through unchanged
- Converts other exceptions → 500 Internal Server Error
- Logs all errors appropriately
- Works with both sync and async functions

---

### **7. Caching Strategy** ([cache.py](app/redis/client.py))

**Pattern:**
```python
# Read operations - cache with TTL
cache_key = f"portfolio:returns:{portfolio_id}:{years}"
cached = await cache.get(cache_key)
if cached:
    return cached

# Compute and cache
data = service.compute()
await cache.set(cache_key, data, ttl=86400)  # 1 day

# Write operations - invalidate cache
await cache.clear_pattern(f"portfolio:returns:{portfolio_id}:*")
```

**Common TTLs:**
- Static data (sectors, industries): 1 day (86400s)
- Performance data: 1 day (86400s)
- Fund data: 1 hour (3600s)
- Factor analysis: 6 hours (21600s)

---

### **8. Registration** ([main.py](main.py:1-101))

```python
from app.api.routes.portfolio_router import router as portfolio_router

app = FastAPI(title="ProphitAI API", version="1.0.0")

# Register routers
app.include_router(portfolio_router, prefix="/api")
```

---

## **How to Build a New Endpoint**

### **Step-by-Step Template:**

**1. Create Router** (`app/api/routes/my_router.py`)
```python
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.api.controller.my_controller import my_controller

router = APIRouter()

class MyRequest(BaseModel):
    field1: str
    field2: int

@router.post("/my-endpoint")
async def my_endpoint(body: MyRequest):
    return await my_controller(
        field1=body.field1,
        field2=body.field2,
    )
```

**2. Create Controller** (`app/api/controller/my_controller.py`)
```python
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.my_service import MyService

@handle_controller_errors
async def my_controller(*, field1: str, field2: int) -> Dict[str, Any]:
    cache_key = f"my:resource:{field1}:{field2}"

    cached = await cache.get(cache_key)
    if cached:
        return cached

    service = MyService(field1=field1, field2=field2)
    data = service.process()

    response = ok_envelope(
        message="Resource retrieved successfully",
        kind="my#resource",
        resource_id=field1,
        self_link=f"/api/my-endpoint",
        payload=data,
    )

    await cache.set(cache_key, response, ttl=3600)
    return response
```

**3. Create Service** (`app/services/my_service.py`)
```python
class MyService:
    def __init__(self, field1: str, field2: int):
        self.field1 = field1
        self.field2 = field2

    def process(self) -> Dict[str, Any]:
        if not self.field1:
            raise ValueError("field1 is required")

        # Business logic here
        result = self._do_something()

        return {"result": result}
```

**4. Register Router** (`main.py`)
```python
from app.api.routes.my_router import router as my_router
app.include_router(my_router, prefix="/api")
```

---

## **Key Patterns to Follow**

✅ **DO:**
- Use `@handle_controller_errors` on all controllers
- Implement caching for read operations
- Invalidate cache on writes
- Use `ok_envelope()` for responses
- Raise `ValueError` in services for validation errors
- Keep routers thin - delegate to controllers
- Use snake_case internally, camelCase for API
- Document cache keys and TTLs

❌ **DON'T:**
- Put business logic in routers
- Put database queries in controllers
- Forget to invalidate cache on mutations
- Mix error handling patterns
- Create backwards compatibility layers (violates CLAUDE.md rules)

---

This architecture ensures **clean separation of concerns**, **consistent error handling**, **efficient caching**, and **maintainable code** following the DRY, KISS, and YAGNI principles from your development guidelines.
