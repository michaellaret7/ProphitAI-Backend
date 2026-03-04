# SnapTrade Broker Integration

## Overview

The SnapTrade broker module (`app/brokers/snaptrade/`) is a universal brokerage aggregation layer that enables ProphitAI to execute trades, manage accounts, and pull reporting data across **any brokerage** supported by SnapTrade (Alpaca, Interactive Brokers, Schwab, TD Ameritrade, etc.) through a single unified API.

**Key principle**: One integration covers all brokers. Users connect their brokerage via SnapTrade's OAuth portal, and ProphitAI interacts with all of them through the same API calls.

---

## Architecture

```
SnapTradeBroker (facade)
├── SnapTradeClient          → SDK initialization + credential management
├── SnapTradeAuth            → User registration, login, deletion, secret management
├── SnapTradeAccounts        → Account info, balances, holdings, positions, orders, activities
├── SnapTradeTrading         → Equity + options order execution, order management
├── SnapTradeConnections     → Brokerage authorization link management
├── SnapTradeReporting       → Cross-account activities + performance reports
└── BrokerOptionsService     → Options chain data (via Alpaca, NOT SnapTrade)
```

### File Structure

| File | Class | Purpose |
|------|-------|---------|
| `client.py` | `SnapTradeClient` | SDK initialization, credential loading |
| `auth.py` | `SnapTradeAuth` | User lifecycle (register, login, delete, reset secret) |
| `accounts.py` | `SnapTradeAccounts` | Account queries (balances, holdings, positions, orders) |
| `trading.py` | `SnapTradeTrading` | Order execution (equities + options) |
| `connections.py` | `SnapTradeConnections` | Brokerage authorization management |
| `reporting.py` | `SnapTradeReporting` | Transaction history + performance reports |
| `broker.py` | `SnapTradeBroker` | Unified facade aggregating all sub-services |
| `utils.py` | — | Pure utility functions (`osi_to_occ`, `extract_body`) |

---

## Authentication & User Model

### Credentials

SnapTrade requires two **partner-level** credentials (set as env vars or passed to constructor):

| Env Var | Description |
|---------|-------------|
| `SNAPTRADE_CLIENT_ID` | Partner client ID issued by SnapTrade |
| `SNAPTRADE_CONSUMER_KEY` | Partner consumer key (secret) |

These authenticate **your application** with SnapTrade. They are NOT per-user credentials.

### Per-User Credentials

Every user in ProphitAI gets their own SnapTrade identity:

| Field | Description | Source |
|-------|-------------|--------|
| `user_id` | Unique identifier (you choose — e.g., a UUID from your DB) | You provide at registration |
| `user_secret` | SnapTrade-generated secret key | Returned by `register_user()` |
| `account_id` | Brokerage account identifier | Returned by `list_accounts()` after connection |

**These three values must be stored in your database per user.** Every API call requires `user_id` + `user_secret`, and trading/account calls additionally require `account_id`.

### User Lifecycle

```python
from app.brokers.snaptrade import SnapTradeBroker

broker = SnapTradeBroker()

# 1. Register user — store the returned user_secret in your DB
result = broker.register_user("user-uuid-from-your-db")
user_secret = result["userSecret"]  # SAVE THIS

# 2. Generate login URL — user opens this in browser to connect their brokerage
login = broker.login_user(user_id, user_secret)
redirect_url = login["redirectURI"]  # Send to frontend / open in browser

# 3. After user connects, fetch their accounts — store account_id(s) in your DB
accounts = broker.list_accounts(user_id, user_secret)
account_id = accounts[0]["id"]  # SAVE THIS

# 4. Now you can trade, query positions, etc.
broker.buy(user_id, user_secret, account_id, symbol="AAPL", units=1)
```

### Resetting a User Secret

```python
result = broker.reset_user_secret(user_id, old_user_secret)
new_secret = result["userSecret"]  # Update in your DB
```

### Deleting a User

```python
broker.delete_user(user_id)  # Removes all SnapTrade data for this user
```

---

## Sub-Service Reference

### SnapTradeClient (`client.py`)

Manages SDK initialization. All other sub-services receive the SDK instance from this client.

```python
from app.brokers.snaptrade.client import SnapTradeClient

client = SnapTradeClient()                     # From env vars
client = SnapTradeClient(client_id="...", consumer_key="...")  # Explicit

sdk = client.get_client()       # Returns SnapTrade SDK instance
cid = client.get_client_id()    # Returns partner client ID string
```

Raises `ValueError` if credentials are missing.

---

### SnapTradeAuth (`auth.py`)

User registration, authentication, and lifecycle management.

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `register_user(user_id)` | `user_id: str` | `{"userId": ..., "userSecret": ...}` | Register new user |
| `login_user(user_id, user_secret, ...)` | `user_id, user_secret`, optional: `broker, connection_type, custom_redirect, reconnect` | `{"redirectURI": ...}` | Generate OAuth login URL |
| `delete_user(user_id)` | `user_id: str` | `dict` | Delete user + all data |
| `list_users()` | — | `List[str]` | List all registered user IDs |
| `reset_user_secret(user_id, user_secret)` | `user_id, user_secret: str` | `{"userId": ..., "userSecret": ...}` | Generate new secret |

**Login optional params:**
- `broker="ALPACA"` — Pre-select a brokerage in the connection portal
- `connection_type="trade"` — Filter to trade-enabled connections only
- `custom_redirect="https://..."` — Redirect URL after connection
- `reconnect="auth-id"` — Re-authorize a disabled connection

---

### SnapTradeAccounts (`accounts.py`)

Account information, balances, positions, orders, and activities.

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `list_accounts(user_id, user_secret)` | — | `List[dict]` | All linked brokerage accounts |
| `get_account_details(user_id, user_secret, account_id)` | — | `dict` | Single account details |
| `get_balances(user_id, user_secret, account_id)` | — | `List[dict]` | Cash balances |
| `get_holdings(user_id, user_secret, account_id)` | — | `dict` | Full holdings (positions + balances + orders) |
| `get_all_holdings(user_id, user_secret)` | — | `List[dict]` | Holdings across ALL accounts |
| `get_positions(user_id, user_secret, account_id)` | — | `List[dict]` | Open positions only |
| `get_orders(user_id, user_secret, account_id, ...)` | optional: `state, days` | `List[dict]` | Order history |
| `get_activities(user_id, user_secret, account_id, ...)` | optional: `start_date, end_date, type` | `List[dict]` | Account activities |

**Order filters:**
- `state` — `"all"`, `"open"`, `"executed"`
- `days` — Lookback window (e.g., `7` for last week)

**Activity filters:**
- `start_date` / `end_date` — `"YYYY-MM-DD"` format
- `type` — Activity type filter (fills, dividends, transfers, etc.)

---

### SnapTradeTrading (`trading.py`)

Order execution for equities and options.

#### Core Method

| Method | Key Args | Description |
|--------|----------|-------------|
| `place_order(...)` | `action, symbol, order_type, time_in_force, units, notional_value, price, stop` | Generic order placement via `place_force_order` |

**Actions:** `"BUY"`, `"SELL"`, `"BUY_TO_OPEN"`, `"SELL_TO_CLOSE"`, `"SELL_TO_OPEN"`, `"BUY_TO_CLOSE"`

**Order types:** `"Market"`, `"Limit"`, `"Stop"`, `"StopLimit"`

**Time in force:** `"Day"`, `"GTC"`, `"FOK"`, `"IOC"`

#### Equity Convenience Methods

```python
# Market buy
trading.buy(user_id, user_secret, account_id, symbol="AAPL", units=1)

# Limit buy
trading.buy(user_id, user_secret, account_id, symbol="MSFT",
            units=1, order_type="Limit", price=400.00)

# Notional buy (dollar amount instead of shares)
trading.buy(user_id, user_secret, account_id, symbol="GOOGL", notional=500.00)

# Sell
trading.sell(user_id, user_secret, account_id, symbol="AAPL", units=1)
```

#### Options Convenience Methods

All option methods accept **OSI symbols** (Alpaca format) and auto-convert to 21-char **OCC format** internally via `osi_to_occ()`.

```python
# Buy to open a call
trading.buy_to_open(user_id, user_secret, account_id,
                    osi_symbol="AAPL260320C00200000", units=1)

# Sell to close
trading.sell_to_close(user_id, user_secret, account_id,
                      osi_symbol="AAPL260320C00200000", units=1)

# Sell to open (write an option)
trading.sell_to_open(user_id, user_secret, account_id,
                     osi_symbol="AAPL260320P00180000", units=1)

# Buy to close
trading.buy_to_close(user_id, user_secret, account_id,
                     osi_symbol="AAPL260320P00180000", units=1)
```

#### Multi-Leg Orders

```python
legs = [
    {"symbol": "AAPL260320C00200000", "action": "BUY_TO_OPEN", "units": 1},
    {"symbol": "AAPL260320C00220000", "action": "SELL_TO_OPEN", "units": 1},
]
trading.place_multi_leg_order(user_id, user_secret, account_id,
                              legs=legs, order_type="Market")
```

> **Known bug**: The SDK expects `instrument` key (not `symbol`) and uppercase order types (`"MARKET"` not `"Market"`) for multi-leg orders. This needs to be fixed in `trading.py`.

#### Order Management

```python
# Cancel an order
trading.cancel_order(user_id, user_secret, account_id, brokerage_order_id="...")

# Replace (modify) an order
trading.replace_order(user_id, user_secret, account_id,
                      brokerage_order_id="...", action="BUY",
                      order_type="Limit", units=1, price=55.00)

# Preview order impact before placing
trading.get_order_impact(user_id, user_secret, account_id,
                         symbol="AAPL", action="BUY", units=1)

# Get quotes
trading.get_quotes(user_id, user_secret, account_id, symbols="AAPL")
trading.get_quotes(user_id, user_secret, account_id, symbols="AAPL,MSFT,GOOGL")
```

---

### SnapTradeConnections (`connections.py`)

Manages brokerage authorization links (the connection between a user and their brokerage).

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `list_authorizations(user_id, user_secret)` | — | `List[dict]` | All brokerage connections |
| `get_authorization(user_id, user_secret, authorization_id)` | — | `dict` | Single connection details |
| `refresh_authorization(user_id, user_secret, authorization_id)` | — | `dict` | Sync latest data from brokerage |
| `disable_authorization(user_id, user_secret, authorization_id)` | — | `dict` | Disable connection (stops syncing) |
| `remove_authorization(user_id, user_secret, authorization_id)` | — | `None` | Permanently remove connection |

> **WARNING**: `disable_authorization` is a **one-way operation**. Once disabled, you CANNOT re-enable programmatically — the user must re-authorize through the SnapTrade OAuth portal using `login_user()` with the `reconnect` parameter. Never call this in automated tests or without explicit user consent.

---

### SnapTradeReporting (`reporting.py`)

Cross-account transaction history and performance analytics.

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `get_activities(user_id, user_secret, ...)` | optional: `start_date, end_date, accounts` | `List[dict]` | Transaction activities across accounts |
| `get_performance_report(user_id, user_secret, start_date, end_date, ...)` | optional: `accounts` | `dict` | Portfolio performance for date range |

**Note:** `get_activities()` here is cross-account (via the reporting API), unlike `accounts.get_activities()` which is per-account.

---

### SnapTradeBroker Facade (`broker.py`)

The `SnapTradeBroker` class is the primary entry point. It exposes every method from all sub-services as top-level methods, so you never need to access sub-services directly (though you can via `broker.auth`, `broker.accounts`, etc.).

```python
from app.brokers.snaptrade import SnapTradeBroker

broker = SnapTradeBroker()

# All these are equivalent:
broker.buy(...)                    # Facade method
broker.trading.buy(...)            # Direct sub-service access
```

#### Constructor

```python
SnapTradeBroker(
    client_id=None,           # Defaults to SNAPTRADE_CLIENT_ID env var
    consumer_key=None,         # Defaults to SNAPTRADE_CONSUMER_KEY env var
    alpaca_options_feed="indicative",  # Alpaca options data feed type
)
```

#### Complete Method Reference

**Auth (5 methods):**
- `register_user(user_id)` → `dict`
- `login_user(user_id, user_secret, broker?, connection_type?, custom_redirect?, reconnect?)` → `dict`
- `delete_user(user_id)` → `dict`
- `list_users()` → `List[str]`
- `reset_user_secret(user_id, user_secret)` → `dict`

**Accounts (8 methods):**
- `list_accounts(user_id, user_secret)` → `List[dict]`
- `get_account_details(user_id, user_secret, account_id)` → `dict`
- `get_balances(user_id, user_secret, account_id)` → `List[dict]`
- `get_holdings(user_id, user_secret, account_id)` → `dict`
- `get_all_holdings(user_id, user_secret)` → `List[dict]`
- `get_positions(user_id, user_secret, account_id)` → `List[dict]`
- `get_orders(user_id, user_secret, account_id, state?, days?)` → `List[dict]`
- `get_account_activities(user_id, user_secret, account_id, start_date?, end_date?, type?)` → `List[dict]`

**Trading — Equities (2 methods):**
- `buy(user_id, user_secret, account_id, symbol, units?, notional?, order_type?, price?, stop?, time_in_force?)` → `dict`
- `sell(user_id, user_secret, account_id, symbol, units?, notional?, order_type?, price?, stop?, time_in_force?)` → `dict`

**Trading — Options (5 methods):**
- `buy_to_open(user_id, user_secret, account_id, osi_symbol, units?, order_type?, price?, time_in_force?)` → `dict`
- `sell_to_close(user_id, user_secret, account_id, osi_symbol, units?, order_type?, price?, time_in_force?)` → `dict`
- `sell_to_open(user_id, user_secret, account_id, osi_symbol, units?, order_type?, price?, time_in_force?)` → `dict`
- `buy_to_close(user_id, user_secret, account_id, osi_symbol, units?, order_type?, price?, time_in_force?)` → `dict`
- `place_multi_leg_order(user_id, user_secret, account_id, legs, order_type?, limit_price?, stop_price?, time_in_force?)` → `dict`

**Trading — Order Management (4 methods):**
- `cancel_order(user_id, user_secret, account_id, brokerage_order_id)` → `dict`
- `replace_order(user_id, user_secret, account_id, brokerage_order_id, action, order_type, ...)` → `dict`
- `get_order_impact(user_id, user_secret, account_id, symbol, action, units, ...)` → `dict`
- `get_quotes(user_id, user_secret, account_id, symbols, use_ticker?)` → `List[dict]`

**Connections (5 methods):**
- `list_connections(user_id, user_secret)` → `List[dict]`
- `get_connection(user_id, user_secret, authorization_id)` → `dict`
- `refresh_connection(user_id, user_secret, authorization_id)` → `dict`
- `disable_connection(user_id, user_secret, authorization_id)` → `dict`
- `remove_connection(user_id, user_secret, authorization_id)` → `None`

**Reporting (2 methods):**
- `get_activities(user_id, user_secret, start_date?, end_date?, accounts?)` → `List[dict]`
- `get_performance_report(user_id, user_secret, start_date, end_date, accounts?)` → `dict`

**Options Data — via Alpaca (5 methods):**
- `get_options_chain(underlying, expiration?, limit?, return_df?)` → `list`
- `get_option_expirations(underlying, start?, end?)` → `List[str]`
- `get_option_contracts(underlying, expiration?, contract_type?, strike_range?, limit?)` → `List[str]`
- `get_option_latest_quote(symbol)` → `dict`
- `get_option_snapshot(symbol)` → `dict`

---

## Utility Functions (`utils.py`)

### `osi_to_occ(osi_symbol: str) -> str`

Converts Alpaca OSI option symbols to 21-character OCC format by padding the root ticker to 6 characters.

```python
osi_to_occ("CRWV260327C00120000")   # → "CRWV  260327C00120000" (21 chars)
osi_to_occ("GOOGL250620C00150000")  # → "GOOGL 250620C00150000" (21 chars)
osi_to_occ("F260115P00010000")      # → "F     260115P00010000" (21 chars)
osi_to_occ("INVALID")               # → ValueError
```

### `extract_body(response: Any) -> Any`

Unwraps `.body` attribute from SnapTrade SDK responses. If the response doesn't have a `.body` attribute, returns it unchanged.

```python
extract_body(sdk_response)  # → sdk_response.body if it exists, else sdk_response
```

---

## Options Data vs Options Execution

This is an important architectural distinction:

| Concern | Provider | Methods |
|---------|----------|---------|
| **Options Data** (chains, quotes, greeks, expirations) | **Alpaca** (direct API) | `get_options_chain`, `get_option_expirations`, `get_option_contracts`, `get_option_latest_quote`, `get_option_snapshot` |
| **Options Execution** (placing orders) | **SnapTrade** (universal) | `buy_to_open`, `sell_to_close`, `sell_to_open`, `buy_to_close`, `place_multi_leg_order` |

**Why?** SnapTrade's options chain endpoint returns 500 for Alpaca Paper, so options DATA comes from Alpaca's native API while options EXECUTION goes through SnapTrade (which works across all connected brokers).

Options data requires separate Alpaca credentials:

| Env Var | Description |
|---------|-------------|
| `ALPACA_API_KEY` | Alpaca API key |
| `ALPACA_SECRET_KEY` | Alpaca secret key |

If these aren't set, `broker.options` will be `None` and all options data methods will raise `RuntimeError`. Options execution still works regardless.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SNAPTRADE_CLIENT_ID` | Yes | SnapTrade partner client ID |
| `SNAPTRADE_CONSUMER_KEY` | Yes | SnapTrade partner consumer key |
| `ALPACA_API_KEY` | No | Alpaca API key (for options data only) |
| `ALPACA_SECRET_KEY` | No | Alpaca secret key (for options data only) |

---

## Per-User Data to Store in Database

When integrating with your user system, store these per user:

| Field | Source | When |
|-------|--------|------|
| `user_id` | You choose (e.g., UUID) | At registration |
| `user_secret` | `register_user()` return value | At registration |
| `account_id(s)` | `list_accounts()` return value | After brokerage connection |

You only need to re-fetch `account_id` if a user adds/removes a brokerage account.

---

## Test Suite

**File:** `tests/brokers/test_snaptrade_broker.py`

Comprehensive integration test suite that runs against the SnapTrade sandbox (Alpaca Paper).

### Test Classes (10 classes, 68 tests)

| Class | Tests | Scope |
|-------|-------|-------|
| `TestUtils` | 10 | `osi_to_occ` (6 variants + 2 error cases) + `extract_body` (2) |
| `TestClientInit` | 4 | Construction from env/explicit, getter, missing creds |
| `TestAuthSubService` | 5 | list, register/delete lifecycle, login, login w/ broker param, reset_secret |
| `TestAccountsSubService` | 10 | All 8 methods + optional param combos (state/days, start/end dates) |
| `TestTradingSubService` | 14 | Equities (market/limit/notional/stop), options (4 intents), multi-leg, cancel, replace, impact, quotes |
| `TestConnectionsSubService` | 3 | list, get, refresh |
| `TestReportingSubService` | 4 | Activities with 3 filter combos + performance report |
| `TestBrokerFacadeInit` | 5 | Sub-service wiring, explicit/missing creds, options presence |
| `TestBrokerFacadeDelegation` | 8 | Delegation spot-checks + RuntimeError when options=None |
| `TestOptionsData` | 5 | Chain, expirations, contracts w/ type filter, quote, snapshot |

### Running Tests

```bash
# All tests
python -m pytest tests/brokers/test_snaptrade_broker.py -v

# Specific class
python -m pytest tests/brokers/test_snaptrade_broker.py::TestTradingSubService -v

# Single test
python -m pytest tests/brokers/test_snaptrade_broker.py::TestUtils::test_osi_to_occ_4char_root -v
```

### Skip Conditions

- **No SnapTrade keys**: Entire file skipped if `SNAPTRADE_CLIENT_ID` not set
- **No Alpaca keys**: `TestOptionsData` and options chain fixtures skipped if `ALPACA_API_KEY` not set

### Sandbox Test Credentials

```python
TEST_USER_ID = "TEST_USER_1"
TEST_USER_SECRET = "7ff3ee67-bf0f-41c0-9d04-cb1de522edfe"
TEST_ACCOUNT_ID = "dff012b2-21ea-4997-9819-5f92f1fbf5f5"
```

### Important Test Safety Notes

- **`disable_authorization` and `remove_authorization` are NOT tested** — they are permanently destructive operations that require manual OAuth re-authorization to undo
- Trading tests place **real sandbox orders** (Alpaca Paper) — no real money, but orders execute
- Uses different symbols for buy vs sell limit tests to avoid SnapTrade's wash trade detection
- Options sell tests try `sell_to_close` first, fall back to `sell_to_open` (sandbox position intent matching)
- Multi-leg and order impact tests catch exceptions gracefully (SDK schema limitations)
- Delegation tests compare types/lengths rather than exact equality (API responses change between calls due to concurrent order activity)

---

## Known Issues / TODOs

1. **Multi-leg order bug**: `place_multi_leg_order` in `trading.py` passes `symbol` key in legs but the SDK expects `instrument`. Also passes `"Market"` but SDK expects `"MARKET"`. Needs fixing.

2. **`get_order_impact` requires UUID**: The method passes a ticker symbol as `universal_symbol_id`, but the SDK expects a SnapTrade universal symbol UUID. Would need a symbol lookup step first.

---

## Usage Examples

### Complete Trading Flow

```python
from app.brokers.snaptrade import SnapTradeBroker

broker = SnapTradeBroker()

user_id = "my-user-uuid"
user_secret = "stored-user-secret"
account_id = "stored-account-id"

# Check positions
positions = broker.get_positions(user_id, user_secret, account_id)

# Buy 10 shares of AAPL
order = broker.buy(user_id, user_secret, account_id, symbol="AAPL", units=10)

# Place a limit sell
order = broker.sell(user_id, user_secret, account_id,
                    symbol="AAPL", units=5,
                    order_type="Limit", price=250.00)

# Check order status
orders = broker.get_orders(user_id, user_secret, account_id,
                           state="open", days=1)

# Cancel if still open
if orders:
    broker.cancel_order(user_id, user_secret, account_id,
                        brokerage_order_id=orders[0]["brokerage_order_id"])
```

### Options Trading Flow

```python
# Get options chain (requires Alpaca keys)
chain = broker.get_options_chain("AAPL", limit=10, return_df=False)

# Find a call to buy
call = chain[0]["symbol"]  # OSI format: "AAPL260320C00200000"

# Buy to open (execution goes through SnapTrade, works on any connected broker)
order = broker.buy_to_open(user_id, user_secret, account_id,
                           osi_symbol=call, units=1)

# Later, sell to close
order = broker.sell_to_close(user_id, user_secret, account_id,
                             osi_symbol=call, units=1)
```

### Querying Account Data

```python
# Balances
balances = broker.get_balances(user_id, user_secret, account_id)

# All holdings (positions + balances + orders)
holdings = broker.get_holdings(user_id, user_secret, account_id)

# Cross-account holdings
all_holdings = broker.get_all_holdings(user_id, user_secret)

# Activities with date filter
activities = broker.get_activities(user_id, user_secret,
                                   start_date="2025-01-01",
                                   end_date="2026-03-04")

# Performance report
report = broker.get_performance_report(user_id, user_secret,
                                        start_date="2025-01-01",
                                        end_date="2026-03-04")
```
