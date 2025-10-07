# ProphitAI API Documentation

**Base URL:** `http://localhost:8000/api`
**Version:** 1.0.0

## Table of Contents
- [Response Envelope Structure](#response-envelope-structure)
- [Authentication](#authentication)
- [User Endpoints](#user-endpoints)
- [Portfolio Endpoints](#portfolio-endpoints)
- [ProphitAlts Endpoints](#prophitalts-endpoints)
- [Agent Runs Endpoints](#agent-runs-endpoints)
- [WebSocket Endpoints](#websocket-endpoints)
- [Error Handling](#error-handling)

---

## Response Envelope Structure

All successful API responses follow a consistent envelope structure:

```json
{
  "status": 200,
  "data": {
    "kind": "resource#type",
    "id": "resource-id",
    "selfLink": "/api/resource/path",
    "updated": "2025-01-15T00:00:00Z",
    "currentItemCount": 10,
    "itemsPerPage": 10,
    "startIndex": 1,
    "totalItems": 10,
    "payload": { /* actual data */ }
  },
  "message": "Success message"
}
```

### Envelope Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | number | HTTP status code (200, 201, etc.) |
| `data.kind` | string | Resource type identifier (e.g., "users#portfolios") |
| `data.id` | string | Resource identifier (optional) |
| `data.selfLink` | string | URL to this resource (optional) |
| `data.updated` | string | RFC3339 timestamp of last update (optional) |
| `data.currentItemCount` | number | Number of items in current response (for lists) |
| `data.itemsPerPage` | number | Items per page (for pagination) |
| `data.startIndex` | number | Starting index (1-based) |
| `data.totalItems` | number | Total number of items available |
| `data.payload` | object/array | The actual response data |
| `message` | string | Human-readable success message |

---

## Authentication

**Current Status:** Authentication is partially implemented using Clerk IDs.

- Most endpoints currently default to hardcoded email: `michaellaret7@gmail.com`
- User endpoints accept `clerkId` query parameter for user identification
- Future: Full authentication middleware with JWT tokens

---

## User Endpoints

### Get User by Clerk ID

**`GET /api/user`**

Retrieve user data by Clerk ID. If user doesn't exist, creates a new user.

**Query Parameters:**
```typescript
{
  clerkId: string;  // Required - User's Clerk ID from frontend
  email?: string;   // Optional - User email from Clerk (for first-login linking)
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "kind": "users#user",
    "id": "uuid",
    "selfLink": "/api/user?clerkId=clerk_xxx",
    "payload": {
      "id": "uuid",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "clerkId": "clerk_xxx",
      "portfolios": [
        {
          "name": "My Portfolio",
          "portfolioId": "uuid",
          "isCurrent": true
        }
      ]
    }
  },
  "message": "User retrieved successfully"
}
```

---

### Get User by Email

**`GET /api/user/email`**

Retrieve complete user data by email address.

**Query Parameters:**
```typescript
{
  email: string;  // Required - User's email address
}
```

**Response:** Same structure as Get User by Clerk ID

---

### Create User

**`POST /api/user`**

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "clerkId": "clerk_xxx"  // Optional
}
```

**Response:**
```json
{
  "status": 201,
  "data": {
    "kind": "users#user",
    "payload": {
      "id": "uuid",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "clerkId": "clerk_xxx"
    }
  },
  "message": "User created successfully"
}
```

---

### Update User

**`PATCH /api/user`**

Update user information.

**Request Body:**
```json
{
  "email": "user@example.com",
  "firstName": "John",      // Optional
  "lastName": "Smith",      // Optional
  "clerkId": "clerk_xxx"    // Optional
}
```

**Response:** Returns updated user data with status 200

---

### Delete User

**`DELETE /api/user`**

Delete a user by Clerk ID.

**Query Parameters:**
```typescript
{
  clerkId: string;  // Required - User's Clerk ID
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "kind": "users#user",
    "payload": null
  },
  "message": "User deleted successfully"
}
```

---

## Portfolio Endpoints

### Get User Portfolios

**`GET /api/portfolios`**

Retrieve all portfolios for a user.

**Query Parameters:**
```typescript
{
  email?: string;  // Optional - Defaults to "michaellaret7@gmail.com"
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "kind": "users#portfolios",
    "id": "user-uuid",
    "selfLink": "/api/user/portfolios?email=user@example.com",
    "currentItemCount": 3,
    "itemsPerPage": 3,
    "startIndex": 1,
    "totalItems": 3,
    "payload": [
      {
        "name": "Tech Growth Portfolio",
        "portfolioId": "uuid",
        "isCurrent": true
      },
      {
        "name": "Dividend Portfolio",
        "portfolioId": "uuid",
        "isCurrent": false
      }
    ]
  },
  "message": "User portfolio list retrieved successfully"
}
```

---

### Create Portfolio

**`POST /api/portfolios`**

Create a new portfolio with positions.

**Request Body:**
```json
{
  "email": "user@example.com",
  "companyName": "Tech Corp",
  "portfolioName": "My Growth Portfolio",
  "positions": [
    {
      "ticker": "AAPL",
      "allocation": 25.5
    },
    {
      "ticker": "MSFT",
      "allocation": 30.0
    },
    {
      "ticker": "GOOGL",
      "allocation": 44.5
    }
  ]
}
```

**Validation:**
- `email`: Required, valid email format
- `companyName`: Required
- `portfolioName`: Required
- `positions`: Required, non-empty array
- Each position must have `ticker` (string) and `allocation` (number)
- Allocations should sum to ~100% (not enforced by API)

**Response:**
```json
{
  "status": 201,
  "data": {
    "kind": "users#portfolios",
    "id": "user-uuid",
    "selfLink": "/api/user/portfolios?email=user@example.com",
    "currentItemCount": 4,
    "itemsPerPage": 4,
    "startIndex": 1,
    "totalItems": 4,
    "payload": [
      /* Updated list of all user portfolios */
    ]
  },
  "message": "Portfolio created successfully"
}
```

---

### Update Portfolio

**`PATCH /api/portfolios`**

Update portfolio name or current status.

**Request Body:**
```json
{
  "email": "user@example.com",
  "portfolioId": "uuid",
  "name": "Updated Portfolio Name",    // Optional
  "isCurrent": true                     // Optional
}
```

**Response:** Returns updated list of all user portfolios with status 200

---

### Delete Portfolio

**`DELETE /api/portfolios`**

Delete a portfolio.

**Request Body:**
```json
{
  "email": "user@example.com",
  "portfolioId": "uuid"
}
```

**Response:** Returns updated list of remaining portfolios with status 200

---

### Get Portfolio Returns

**`GET /api/portfolios/{portfolioId}/returns`**

Calculate and retrieve historical returns for a portfolio.

**Path Parameters:**
- `portfolioId`: UUID of the portfolio

**Query Parameters:**
```typescript
{
  years?: number;  // Optional - Number of years of historical data (1-10), defaults to 2
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "kind": "portfolio#returns",
    "id": "portfolio-uuid",
    "selfLink": "/api/portfolio/returns?portfolioId=uuid",
    "payload": [
      {
        "date": "2023-01-03",
        "cumulativeReturn": 1.025,
        "nav": 1025000.00
      },
      {
        "date": "2023-01-04",
        "cumulativeReturn": 1.032,
        "nav": 1032000.00
      }
      /* ... daily data points */
    ]
  },
  "message": "Portfolio returns retrieved successfully"
}
```

**Return Data Fields:**
- `date`: ISO date string (YYYY-MM-DD)
- `cumulativeReturn`: Cumulative return multiplier (1.0 = no change, 1.5 = 50% gain)
- `nav`: Net Asset Value starting from $1,000,000 initial investment

**Notes:**
- Daily frequency data
- Uses weighted returns based on position allocations
- NAV progression starts at $1,000,000
- Returns `null` for values that are not finite (NaN, Infinity)

---

## ProphitAlts Endpoints

### Get Fund Performance Data

**`GET /api/alts/fund/{fund_name}/data`**

Retrieve comprehensive performance data and positions for a specific fund.

**Path Parameters:**
- `fund_name`: Name of the fund (e.g., "consumer_staples_fund")

**Response:**
```json
{
  "status": 200,
  "data": {
    "kind": "prophitAlts#fundPerformance",
    "id": "consumer_staples_fund",
    "selfLink": "/api/alts/fund/consumer_staples_fund/data",
    "updated": "2025-01-15T00:00:00Z",
    "currentItemCount": 6,
    "itemsPerPage": 6,
    "startIndex": 1,
    "totalItems": 6,
    "payload": {
      "metrics": {
        "ytdReturn": 15.23,
        "grossExposure": 150.5,
        "netExposure": 50.2,
        "sharpeRatio": 1.85,
        "sortinoRatio": 2.34,
        "maxDrawdown": -12.5,
        "beta": 0.85,
        "upCapture": 95.2,
        "downCapture": 78.3,
        "var95": -2.5
      },
      "performanceData": [
        {
          "tickerName": "AAPL",
          "position": "Long",
          "industry": "Technology",
          "riskAllocation": 12.5,
          "portfolioAllocation": 15.3
        }
      ],
      "navPerformanceDaily": [
        {
          "date": "2023-01-03",
          "nav": 1000000,
          "return": 0.0
        }
      ],
      "rolling12mReturnsDaily": [
        {
          "date": "2023-01-03",
          "return": 12.5
        }
      ],
      "monthlyReturnHistory": [
        {
          "month": "2023-01",
          "return": 2.5
        }
      ],
      "underwaterDaily": [
        {
          "date": "2023-01-03",
          "drawdown": -5.2
        }
      ],
      "returnDistribution": [
        {
          "binStart": -2.0,
          "binEnd": -1.0,
          "count": 5
        }
      ]
    }
  },
  "message": "Fund final positions retrieved successfully"
}
```

**Metrics Explanation:**
- `ytdReturn`: Year-to-date return (%)
- `grossExposure`: Total long + short exposure (%)
- `netExposure`: Long minus short exposure (%)
- `sharpeRatio`: Risk-adjusted return metric
- `sortinoRatio`: Downside risk-adjusted return
- `maxDrawdown`: Maximum peak-to-trough decline (%)
- `beta`: Correlation to market benchmark
- `upCapture`: Performance in up markets (%)
- `downCapture`: Performance in down markets (%)
- `var95`: Value at Risk at 95% confidence level

**Performance Data Fields:**
- `tickerName`: Stock ticker symbol
- `position`: "Long" or "Short"
- `industry`: Industry sector
- `riskAllocation`: Risk-based allocation (%)
- `portfolioAllocation`: Portfolio weight (%)

**Time Series Data:**
All time series are arrays of objects with specific structures as shown above. Use for charting and analysis.

---

### Get All Funds

**`GET /api/alts/funds`**

Retrieve list of all available funds.

**Response:**
```json
{
  "status": 200,
  "data": {
    "kind": "prophitAlts#fundTable",
    "id": "funds",
    "selfLink": "/api/alts/funds",
    "payload": [
      {
        "fundName": "consumer_staples_fund",
        "displayName": "Consumer Staples Long/Short",
        "strategy": "Sector-focused alternative investment"
      }
    ]
  },
  "message": "Fund table retrieved successfully"
}
```

---

## Agent Runs Endpoints

### Create Optimizer Agent Run

**`POST /api/agents/optimizer/runs`**

Start a new optimizer agent run for portfolio optimization.

**Request Body:** None required (uses built-in prompts)

**Response:**
```json
{
  "run_id": "uuid"
}
```

**Notes:**
- Returns immediately with a `run_id`
- Agent execution happens asynchronously
- Use WebSocket connection to monitor progress (see WebSocket section)

---

## WebSocket Endpoints

### Stream Agent Evidence

**`WS /ws/agents/{run_id}`**

WebSocket connection for real-time agent execution streaming.

**Connection URL:**
```
ws://localhost:8000/api/ws/agents/{run_id}
```

**Usage:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/ws/agents/${runId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Agent update:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Agent execution completed');
};
```

**Message Format:**
Messages sent through the WebSocket contain agent execution updates including:
- Tool calls
- Agent reasoning
- Task progress
- Final results

---

## Error Handling

All error responses follow this structure:

```json
{
  "error": {
    "code": 400,
    "message": "Detailed error message",
    "errors": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### Common HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid request body, missing required fields |
| 404 | Not Found | Resource doesn't exist (user, portfolio, fund) |
| 422 | Unprocessable Entity | Validation error (Pydantic validation failed) |
| 500 | Internal Server Error | Server-side error, database issues |

### Error Response Examples

**400 Bad Request:**
```json
{
  "error": {
    "code": 400,
    "message": "Email is required",
    "errors": []
  }
}
```

**404 Not Found:**
```json
{
  "error": {
    "code": 404,
    "message": "Portfolio not found",
    "errors": []
  }
}
```

**422 Validation Error (FastAPI/Pydantic):**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## CORS Configuration

**Allowed Origins:** `http://localhost:5173` (Vite dev server)
**Credentials:** Enabled
**Methods:** All (`*`)
**Headers:** All (`*`)

**Note:** Update `allow_origins` in [main.py](main.py) for production deployment.

---

## Data Type Conventions

### Naming Convention
- **API Request/Response:** `camelCase` (e.g., `portfolioId`, `firstName`)
- **Database/Internal:** `snake_case` (e.g., `portfolio_id`, `first_name`)
- Controllers handle the conversion between conventions

### UUID Format
All IDs are UUID v4 strings:
```typescript
type UUID = string;  // e.g., "550e8400-e29b-41d4-a716-446655440000"
```

### Date Formats
- **ISO Date:** `YYYY-MM-DD` (e.g., "2025-01-15")
- **ISO DateTime (RFC3339):** `YYYY-MM-DDTHH:mm:ssZ` (e.g., "2025-01-15T14:30:00Z")

### Percentage Values
Percentages are represented as numbers:
- `25.5` represents 25.5%
- `100.0` represents 100%
- Display with `%` symbol in UI

---

## Rate Limiting

**Current Status:** Not implemented
**Future:** Rate limiting will be added per user/API key

---

## Versioning

**Current Version:** 1.0.0
**Strategy:** URL-based versioning will be implemented (e.g., `/api/v1/`, `/api/v2/`)

---

## TypeScript Types

### User Types
```typescript
interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  clerkId?: string;
  portfolios?: Portfolio[];
}

interface Portfolio {
  name: string;
  portfolioId: string;
  isCurrent: boolean;
}
```

### Portfolio Types
```typescript
interface Position {
  ticker: string;
  allocation: number;  // Percentage (0-100)
}

interface CreatePortfolioRequest {
  email: string;
  companyName: string;
  portfolioName: string;
  positions: Position[];
}

interface PortfolioReturn {
  date: string;  // ISO date
  cumulativeReturn: number | null;
  nav: number | null;
}
```

### Fund Types
```typescript
interface FundMetrics {
  ytdReturn?: number;
  grossExposure?: number;
  netExposure?: number;
  sharpeRatio?: number;
  sortinoRatio?: number;
  maxDrawdown?: number;
  beta?: number;
  upCapture?: number;
  downCapture?: number;
  var95?: number;
}

interface FundPosition {
  tickerName: string;
  position: "Long" | "Short";
  industry: string;
  riskAllocation: number;
  portfolioAllocation: number;
}

interface FundPerformanceData {
  metrics: FundMetrics;
  performanceData: FundPosition[];
  navPerformanceDaily?: TimeSeriesPoint[];
  rolling12mReturnsDaily?: TimeSeriesPoint[];
  monthlyReturnHistory?: TimeSeriesPoint[];
  underwaterDaily?: TimeSeriesPoint[];
  returnDistribution?: HistogramBin[];
}

interface TimeSeriesPoint {
  date: string;
  [key: string]: number | string;
}

interface HistogramBin {
  binStart: number;
  binEnd: number;
  count: number;
}
```

### Response Envelope Types
```typescript
interface ApiResponse<T> {
  status: number;
  data: {
    kind?: string;
    id?: string;
    selfLink?: string;
    updated?: string;
    currentItemCount?: number;
    itemsPerPage?: number;
    startIndex?: number;
    totalItems?: number;
    payload: T;
  };
  message: string;
}

interface ApiError {
  error: {
    code: number;
    message: string;
    errors: Array<{
      field?: string;
      message: string;
    }>;
  };
}
```

---

## Testing

### Manual Testing
Test endpoints are available at:
- [Portfolio Testing](app/api/testing/portfolio_testing.py)
- [User Testing](app/api/testing/user_testing.py)
- [Alts Testing](app/api/testing/alts_testing.py)

### Interactive API Docs
FastAPI provides automatic interactive documentation:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Development Server

**Start Server:**
```bash
source .venv/bin/activate
python main.py
```

**Default Port:** 8000
**Health Check:** `http://localhost:8000/health`

---

## Additional Resources

- **Pydantic Docs:** https://docs.pydantic.dev/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Project Guidelines:** [.claude/CLAUDE.md](.claude/CLAUDE.md)
