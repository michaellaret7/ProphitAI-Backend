# Broker Connectivity — Frontend Integration Spec

## Overview

Brokerage account connection is now **optional**. Users can use ProphitAI without connecting a broker. All broker-dependent features gracefully degrade — the API returns structured, predictable responses that the frontend can detect and use to show appropriate UI (e.g., "Connect Broker" CTAs instead of error toasts).

---

## How to Detect Broker Connection Status

### Option 1: Check Connection Status Endpoint

```
GET /api/broker/connection-status
```

**Response (200):**
```json
{
  "status": 200,
  "data": {
    "kind": "broker#connectionStatus",
    "selfLink": "/api/broker/connection-status",
    "payload": {
      "registered": false,
      "connected": false,
      "account_id": null
    }
  },
  "message": "Connection status retrieved successfully"
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `registered` | `boolean` | User has started SnapTrade registration (has user_id + user_secret) |
| `connected` | `boolean` | User has completed OAuth and has a linked brokerage account |
| `account_id` | `string \| null` | The SnapTrade account ID, or null if not connected |

**Use this on app load / session start** to determine whether to show broker UI or connection prompts.

### Option 2: Dashboard Payload

The dashboard response now includes a top-level `brokerConnected` field:

```
GET /api/dashboard
```

**Response (200):**
```json
{
  "status": 200,
  "data": {
    "kind": "dashboard#overview",
    "payload": {
      "brokerConnected": false,
      "account": {
        "equity": null,
        "buyingPower": null,
        "cash": null,
        "dayPnl": null
      },
      "portfolioPerformance": null,
      "positions": null,
      "sectorBreakdown": null,
      "industryBreakdown": null,
      "marketOverview": {
        "indices": [...],
        "treasuryRates": {...}
      },
      "recentOrders": null,
      "news": {
        "general": [...],
        "holdings": null
      }
    }
  }
}
```

When `brokerConnected` is `false`:
- `account.equity`, `account.buyingPower`, `account.cash`, `account.dayPnl` → `null`
- `positions` → `null`
- `portfolioPerformance` → `null`
- `recentOrders` → `null`
- `sectorBreakdown`, `industryBreakdown` → `null`
- `news.holdings` → `null`

**Market data is always populated regardless of broker status:**
- `marketOverview.indices` → always has SPY, QQQ, DIA, IWM, GLD quotes
- `marketOverview.treasuryRates` → always has latest treasury rates
- `news.general` → always has general market news

---

## Broker-Required API Endpoints

The following endpoints return **HTTP 422** when the user has no connected broker:

### Account & Balances
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/broker/account` | Full broker account info |
| `GET` | `/api/broker/account/balances` | Cash, buying power, equity |

### Trading
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/broker/orders/buy` | Place a buy order |
| `POST` | `/api/broker/orders/sell` | Place a sell order |
| `GET` | `/api/broker/orders` | List orders |
| `DELETE` | `/api/broker/orders/{orderId}` | Cancel an order |

### Positions
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/broker/positions` | List all positions |
| `GET` | `/api/broker/positions/{symbol}` | Get single position |
| `DELETE` | `/api/broker/positions/{symbol}` | Close a position |

### Portfolio
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/broker/portfolio/history` | Historical performance |

### Trade Proposals
| Method | Path | Purpose |
|--------|------|---------|
| `PATCH` | `/api/trade-proposals/{id}/approve` | Approve and execute a trade proposal |

---

## The 422 Error Response

When any of the above endpoints is called without a connected broker, the API returns:

```
HTTP 422 Unprocessable Entity
```

```json
{
  "error": {
    "code": 422,
    "message": "No brokerage account is connected. Connect a broker in your account settings to enable trading, positions, and order management.",
    "errors": [
      {
        "reason": "broker_not_connected"
      }
    ]
  }
}
```

### How to Detect in Frontend Code

```typescript
// Check for broker not connected error
function isBrokerNotConnected(error: AxiosError): boolean {
  if (error.response?.status !== 422) return false;

  const detail = error.response.data?.detail || error.response.data;
  const errors = detail?.error?.errors;

  return Array.isArray(errors) && errors.some(e => e.reason === "broker_not_connected");
}
```

**The machine-readable key is `errors[0].reason === "broker_not_connected"`**. Do not parse the `message` string — it may change. The `reason` field is the stable contract.

---

## Endpoints That Work Without a Broker

These endpoints are **not affected** and work normally regardless of broker status:

### Connection Flow (used to connect a broker)
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/broker/connection-status` | Check if broker is connected |
| `POST` | `/api/broker/snaptrade/register` | Register with SnapTrade |
| `POST` | `/api/broker/snaptrade/connect` | Get OAuth redirect URL |
| `POST` | `/api/broker/snaptrade/callback` | Save account after OAuth |
| `GET` | `/api/broker/connections` | List broker connections |
| `DELETE` | `/api/broker/connections/{id}` | Remove a connection |

### Trade Proposals (read/reject only)
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/trade-proposals` | List proposals (DB-only) |
| `GET` | `/api/trade-proposals/{id}` | Get single proposal (DB-only) |
| `PATCH` | `/api/trade-proposals/{id}/reject` | Reject a proposal (DB-only) |

### Everything Else
All non-broker endpoints work normally: portfolio analytics, prices, fundamentals, screeners, news, chat, search, watchlist, etc.

---

## Recommended Frontend Behavior

### Dashboard
When `brokerConnected` is `false`:
- Show market overview (indices, treasury rates, news) normally
- Replace the account summary / positions / orders sections with a "Connect Your Broker" card
- Don't show empty tables or zero values — show a clear CTA

### Broker Pages (Positions, Orders, Portfolio History)
- Check `brokerConnected` from the dashboard cache or call `/broker/connection-status`
- If not connected, show a full-page connection prompt instead of loading the page
- Alternatively, catch the 422 response and render the connection prompt

### Trade Proposals
- The proposals list (`GET /trade-proposals`) works without a broker — users can still see proposals
- The "Approve" action will return 422 if no broker is connected — show a prompt to connect first
- The "Reject" action works regardless

### Chat / Agent
- The agent handles this automatically — when broker tools are unavailable, the agent informs the user they can connect a broker and offers to help with non-broker features instead
- No frontend changes needed for the chat flow

### Navigation / Sidebar
- Consider dimming or badging broker-specific nav items when not connected
- The connection status can be fetched once at app load and stored in global state

---

## Error Response Comparison

| Scenario | HTTP Status | `errors[0].reason` |
|----------|-------------|---------------------|
| No broker connected | **422** | `"broker_not_connected"` |
| Missing required param (e.g., no clerk_id) | 400 | N/A (plain string detail) |
| Broker API failure (timeout, auth issue) | 500 | N/A |
| Order rejected by broker | 400 | N/A |
| Trade proposal execution failed | 502 | N/A |

The 422 with `broker_not_connected` is the **only** response that means "the user needs to connect a broker." All other errors are operational failures that should be shown as error toasts.

---

## State Diagram

```
User signs up
    │
    ▼
┌──────────────────────┐
│  No Broker Connected │  ← connection-status: { registered: false, connected: false }
│                      │  ← Dashboard: brokerConnected: false
│  - Market data works │  ← Broker endpoints return 422
│  - Chat works        │
│  - Research works    │
│  - Screeners work    │
└──────────┬───────────┘
           │ User clicks "Connect Broker"
           ▼
┌──────────────────────┐
│  Registration        │  POST /broker/snaptrade/register
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  OAuth Flow          │  POST /broker/snaptrade/connect → redirect
│                      │  POST /broker/snaptrade/callback → save account
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Broker Connected    │  ← connection-status: { registered: true, connected: true }
│                      │  ← Dashboard: brokerConnected: true
│  - Everything works  │  ← All endpoints return normal data
└──────────────────────┘
```
