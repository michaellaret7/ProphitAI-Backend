# ProphitAI API Documentation

**Base URL:** `http://localhost:8000`
**API Version:** 1.0.0
**Response Format:** All responses follow a standardized envelope pattern with `status`, `data`, and `message` fields.

---

## Response Envelope Structure

### Success Response
```json
{
  "status": 200,
  "message": "OK",
  "data": {
    "kind": "resource#type",
    "id": "resource-identifier",
    "selfLink": "/api/endpoint",
    "updated": "2025-01-15T00:00:00Z",
    "currentItemCount": 10,
    "itemsPerPage": 10,
    "startIndex": 1,
    "totalItems": 10,
    "payload": {}
  }
}
```

### Error Response
```json
{
  "error": {
    "code": 404,
    "message": "Resource not found",
    "errors": []
  }
}
```

---

## 🟢 PRODUCTION-READY ENDPOINTS

These endpoints are fully implemented, tested, and ready for frontend integration.

---

### **1. User Management**

#### **GET /api/user**
Get user by Clerk ID. Auto-creates user if not found (first-login flow).

**Query Parameters:**
- `clerkId` (required): User's Clerk authentication ID
- `email` (optional): Email for first-login auto-creation

**Response (200):**
```json
{
  "status": 200,
  "message": "User data retrieved successfully",
  "data": {
    "kind": "users#user",
    "id": "uuid",
    "selfLink": "/api/user?clerkId=clerk_xxx",
    "payload": {
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "companies": [
        {"id": "company-uuid"}
      ]
    }
  }
}
```

**Status:** ✅ **READY** - Fully implemented with auto-creation on first login

---

#### **GET /api/user/email**
Get user data by email address.

**Query Parameters:**
- `email` (required): User's email address

**Response (200):**
```json
{
  "status": 200,
  "message": "User data retrieved successfully",
  "data": {
    "kind": "users#user",
    "id": "uuid",
    "selfLink": "/api/user/email?email=user@example.com",
    "payload": {
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "companies": [
        {"id": "company-uuid"}
      ]
    }
  }
}
```

**Status:** ✅ **READY** - Fully implemented

---

#### **POST /api/user**
Create a new user.

**Request Body:**
```json
{
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "clerkId": "clerk_xxx" // optional
}
```

**Response (201):**
```json
{
  "status": 201,
  "message": "User created successfully",
  "data": {
    "kind": "users#user",
    "id": "user@example.com",
    "selfLink": "/api/user",
    "payload": {
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "clerkId": "clerk_xxx"
    }
  }
}
```

**Status:** ✅ **READY** - Auto-assigns to ProphitAI company with admin role

---

#### **PATCH /api/user**
Update user information.

**Request Body:**
```json
{
  "email": "user@example.com",
  "firstName": "John",    // optional
  "lastName": "Doe",      // optional
  "clerkId": "clerk_xxx"  // optional
}
```

**Response (200):**
```json
{
  "status": 200,
  "message": "User updated successfully",
  "data": {
    "kind": "users#user",
    "id": "clerk_xxx",
    "selfLink": "/api/user",
    "payload": {
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe"
    }
  }
}
```

**Status:** ✅ **READY** - Fully implemented

---

#### **DELETE /api/user**
Delete user by Clerk ID.

**Query Parameters:**
- `clerkId` (required): User's Clerk ID

**Response (200):**
```json
{
  "status": 200,
  "message": "User deleted successfully",
  "data": {
    "kind": "users#user",
    "id": "clerk_xxx",
    "selfLink": "/api/user?clerkId=clerk_xxx",
    "payload": {}
  }
}
```

**Status:** ✅ **READY** - Fully implemented

---

### **2. Portfolio Management**

#### **GET /api/portfolios**
Get all portfolios for a user.

**Query Parameters:**
- `email` (required): User's email address

**Response (200):**
```json
{
  "status": 200,
  "message": "User portfolio list retrieved successfully",
  "data": {
    "kind": "users#portfolios",
    "id": "user-uuid",
    "selfLink": "/api/user/portfolios?email=user@example.com",
    "currentItemCount": 2,
    "itemsPerPage": 2,
    "startIndex": 1,
    "totalItems": 2,
    "payload": [
      {
        "name": "Growth Portfolio",
        "portfolioId": "portfolio-uuid",
        "isCurrent": true
      },
      {
        "name": "Income Portfolio",
        "portfolioId": "portfolio-uuid-2",
        "isCurrent": false
      }
    ]
  }
}
```

**Status:** ✅ **READY** - Fully implemented

**TODO Note:** Currently missing returns and other metrics in payload (commented in code)

---

#### **POST /api/portfolios**
Create a new portfolio.

**Request Body:**
```json
{
  "email": "user@example.com",
  "companyName": "ProphitAI",
  "portfolioName": "My Portfolio",
  "positions": [
    {
      "ticker": "AAPL",
      "allocation": 0.30
    },
    {
      "ticker": "MSFT",
      "allocation": 0.70
    }
  ]
}
```

**Response (201):**
```json
{
  "status": 201,
  "message": "Portfolio created successfully",
  "data": {
    "kind": "users#portfolios",
    "id": "user-uuid",
    "selfLink": "/api/user/portfolios?email=user@example.com",
    "currentItemCount": 1,
    "itemsPerPage": 1,
    "startIndex": 1,
    "totalItems": 1,
    "payload": [
      {
        "name": "My Portfolio",
        "portfolioId": "portfolio-uuid",
        "isCurrent": false
      }
    ]
  }
}
```

**Status:** ✅ **READY** - Fully implemented with position validation

---

#### **PATCH /api/portfolios**
Update portfolio name or set as current.

**Request Body:**
```json
{
  "email": "user@example.com",
  "portfolioId": "portfolio-uuid",
  "name": "Updated Name",    // optional
  "isCurrent": true          // optional
}
```

**Response (200):**
```json
{
  "status": 200,
  "message": "Portfolio updated successfully",
  "data": {
    "kind": "users#portfolios",
    "id": "user-uuid",
    "selfLink": "/api/user/portfolios?email=user@example.com",
    "payload": [
      {
        "name": "Updated Name",
        "portfolioId": "portfolio-uuid",
        "isCurrent": true
      }
    ]
  }
}
```

**Status:** ✅ **READY** - Fully implemented

---

#### **DELETE /api/portfolios**
Delete a portfolio.

**Request Body:**
```json
{
  "email": "user@example.com",
  "portfolioId": "portfolio-uuid"
}
```

**Response (200):**
```json
{
  "status": 200,
  "message": "Portfolio deleted successfully",
  "data": {
    "kind": "users#portfolios",
    "id": "user-uuid",
    "selfLink": "/api/user/portfolios?email=user@example.com",
    "payload": []
  }
}
```

**Status:** ✅ **READY** - Fully implemented

---

#### **POST /api/portfolios/returns**
Get cumulative returns for a portfolio over the last 2 years.

**Request Body:**
```json
{
  "email": "user@example.com",
  "portfolioId": "portfolio-uuid"
}
```

**Response (200):**
```json
{
  "status": 200,
  "message": "Portfolio returns retrieved successfully",
  "data": {
    "kind": "portfolio#returns",
    "id": "portfolio-uuid",
    "selfLink": "/api/portfolio/returns?email=user@example.com&portfolioId=portfolio-uuid",
    "payload": [
      {
        "date": "2023-01-01",
        "cumulativeReturn": 1.0
      },
      {
        "date": "2023-01-02",
        "cumulativeReturn": 1.015
      },
      {
        "date": "2023-01-03",
        "cumulativeReturn": 1.028
      }
    ]
  }
}
```

**Status:** ✅ **READY** - Fully implemented with 2-year daily returns

**Notes:**
- Fetches last 2 years of daily price data
- Calculates weighted daily returns with daily renormalization
- Returns cumulative return time series
- Handles missing data gracefully

---

### **3. Alternative Investments (ProphitAlts)**

#### **GET /api/alts/funds**
Get all available alternative investment funds.

**Response (200):**
```json
{
  "status": 200,
  "message": "Fund table retrieved successfully",
  "data": {
    "kind": "prophitAlts#fundTable",
    "id": "funds",
    "selfLink": "/api/alts/funds",
    "payload": [
      {
        "fundName": "Consumer Staples Fund",
        "strategy": "Long/Short Equity",
        "aum": 1500000000
      }
    ]
  }
}
```

**Status:** ✅ **READY** - Fully implemented

---

#### **GET /api/alts/fund/{fund_name}/data**
Get comprehensive fund performance data including positions, metrics, and time-series data.

**Path Parameters:**
- `fund_name` (required): Name of the fund (e.g., "Consumer Staples Fund")

**Response (200):**
```json
{
  "status": 200,
  "message": "Fund final positions retrieved successfully",
  "data": {
    "kind": "prophitAlts#fundPerformance",
    "id": "Consumer Staples Fund",
    "selfLink": "/api/alts/fund/Consumer Staples Fund/data",
    "updated": "2025-01-15T00:00:00Z",
    "currentItemCount": 5,
    "itemsPerPage": 5,
    "startIndex": 1,
    "totalItems": 5,
    "payload": {
      "metrics": {
        "ytdReturn": 12.5,
        "grossExposure": 150.0,
        "netExposure": 100.0,
        "sharpeRatio": 1.8,
        "sortinoRatio": 2.3,
        "maxDrawdown": -8.5,
        "beta": 0.85,
        "upCapture": 105.0,
        "downCapture": 65.0,
        "var95": -2.1
      },
      "performanceData": [
        {
          "tickerName": "AAPL",
          "position": "long",
          "industry": "Technology",
          "riskAllocation": 0.150,
          "portfolioAllocation": 0.200
        }
      ],
      "navPerformanceDaily": [
        {
          "date": "2024-01-01",
          "nav": 100.0
        },
        {
          "date": "2024-01-02",
          "nav": 101.5
        }
      ],
      "rolling12mReturnsDaily": [
        {
          "date": "2024-01-01",
          "return": 0.125
        }
      ],
      "monthlyReturnHistory": [
        {
          "month": "2024-01",
          "return": 0.025
        }
      ],
      "underwaterDaily": [
        {
          "date": "2024-01-01",
          "drawdown": -0.05
        }
      ],
      "returnDistribution": [
        {
          "binStart": -0.02,
          "binEnd": -0.01,
          "count": 5
        },
        {
          "binStart": -0.01,
          "binEnd": 0.0,
          "count": 12
        }
      ]
    }
  }
}
```

**Status:** ✅ **READY** - Fully implemented with comprehensive metrics

**Notes:**
- Returns portfolio positions with industry/allocation data
- Includes 10+ performance metrics (Sharpe, Sortino, VaR, Beta, etc.)
- Time-series data: NAV performance, rolling returns, drawdowns
- Return distribution histogram for risk visualization
- All keys converted to camelCase for frontend consistency

---

### **4. WebSocket - Agent Streaming**

#### **WS /api/ws/agents/{run_id}**
Real-time streaming of agent execution output.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/agents/{run_id}');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  // Handle agent output
};
```

**Message Format:**
```json
{
  "type": "agent_output",
  "content": "Agent reasoning step...",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status:** ✅ **READY** - WebSocket manager service fully implemented

**Notes:**
- Supports multiple concurrent connections per run_id
- Auto-cleanup on disconnect
- Used for real-time agent execution monitoring

---

### **5. Agent Runs**

#### **POST /api/agents/optimizer/runs**
Create and start an optimizer agent run.

**Response (200):**
```json
{
  "run_id": "uuid-v4"
}
```

**Status:** ✅ **READY** - Agent framework operational

**Usage Flow:**
1. POST to create agent run → Receive `run_id`
2. Connect to WebSocket at `/api/ws/agents/{run_id}`
3. Receive real-time agent output via WebSocket

---

## 🟡 INCOMPLETE / NEEDS WORK

These endpoints have TODOs or are partially implemented.

### **Portfolio Endpoints**

#### **TODO: GET /api/portfolios (by UUID)**
Currently uses email, needs to support UUID-based retrieval.

**Location:** `portfolio_router.py:38`

---

#### **TODO: Enhanced Portfolio List Response**
Add returns and other metrics to portfolio list payload.

**Location:** `portfolio_controller.py:25`
**Current Response Missing:**
- YTD returns
- Total return
- Sharpe ratio
- Volatility
- Last updated date

---

## 📋 Summary for Frontend Developer

### **What's Ready to Connect:**

✅ **User Authentication Flow (Clerk Integration)**
- `GET /api/user?clerkId={id}` - Auto-creates users on first login
- `POST /api/user` - Manual user creation
- `PATCH /api/user` - Update user info
- `DELETE /api/user` - Remove users

✅ **Portfolio CRUD Operations**
- `GET /api/portfolios?email={email}` - List all portfolios
- `POST /api/portfolios` - Create portfolio with positions
- `PATCH /api/portfolios` - Update name or set as current
- `DELETE /api/portfolios` - Remove portfolio

✅ **Portfolio Analytics**
- `POST /api/portfolios/returns` - 2-year cumulative return time series

✅ **Alternative Investments (ProphitAlts)**
- `GET /api/alts/funds` - List all alt funds
- `GET /api/alts/fund/{fund_name}/data` - Comprehensive fund performance data with metrics, positions, and time-series

✅ **Real-Time Agent Streaming**
- `POST /api/agents/optimizer/runs` - Start agent run
- `WS /api/ws/agents/{run_id}` - Stream agent output

---

### **What's Missing:**

⚠️ **Portfolio Endpoints**
- Portfolio retrieval by UUID (currently requires email)
- Extended metrics in portfolio list (returns, Sharpe, volatility)

⚠️ **Authentication**
- No JWT/session management implemented
- CORS currently only allows `localhost:5173`
- Production auth needs implementation

⚠️ **Rate Limiting**
- No rate limiting implemented

⚠️ **Pagination**
- Response envelope supports pagination metadata, but not implemented in endpoints

---

### **Integration Notes:**

1. **CORS:** Currently configured for `http://localhost:5173` only
2. **Error Handling:** All endpoints use standardized error responses
3. **Camel Case:** All response keys are in camelCase for JS/TS compatibility
4. **Date Format:** ISO 8601 / RFC3339 format
5. **Response Envelope:** All responses follow Google JSON Style Guide pattern

---

### **Environment Setup:**

```bash
# Base URL
API_BASE_URL=http://localhost:8000

# WebSocket URL
WS_BASE_URL=ws://localhost:8000
```

---

### **Testing Endpoints:**

FastAPI provides automatic interactive API docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Stock Screener - Troubleshooting Empty Results

- Use exact sector tokens: `equity_sector_*` (e.g., `equity_sector_health_care`).
- For ETFs, set `sector="etf"`; use ETF industries like `equity_etfs` or `fixed_income_etfs`.
- Expense ratio and AUM fields may be sparse; relax or remove those filters if no results.
- The screener now returns `warnings` in responses when results are empty to guide adjustments.

---

### **Questions or Issues:**

Contact backend team for:
- Adding new endpoints
- Modifying response schemas
- CORS configuration for production
- Authentication implementation
