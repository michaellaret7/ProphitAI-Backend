# Alpaca → SnapTrade Migration Plan

## Context

ProphitAI uses Alpaca Broker API for multi-user brokerage operations (trading, positions, accounts, funding). We're replacing it entirely with SnapTrade — a universal brokerage aggregation layer that lets users connect any supported brokerage (Alpaca, IBKR, Schwab, etc.) via OAuth. The SnapTrade broker module (`app/brokers/snaptrade/`) is already built and tested; this migration wires it into the existing application layers and removes all Alpaca code.

**Key architectural shift**: SnapTrade requires `user_id` + `user_secret` per API call (vs Alpaca's single `account_id`). Every layer must pass this credential triple.

---

## Phase 1: Pre-Migration (Preserve dependencies before deletion)

### 1A. Move `BrokerOptionsService` + `decode_osi` to SnapTrade module

SnapTrade's `broker.py:70` imports `BrokerOptionsService` from `alpaca_broker`. Move it before deleting Alpaca.

- **Copy** `app/brokers/alpaca_broker/options.py` → `app/brokers/snaptrade/options.py`
  - Includes `BrokerOptionsService` class and `decode_osi` function
  - Also copy the `_OSI` regex and `date` import it depends on
- **Update** `app/brokers/snaptrade/broker.py:70`: change import to `from app.brokers.snaptrade.options import BrokerOptionsService`
- **Update** `app/repositories/options.py:5`: change import to `from app.brokers.snaptrade.options import decode_osi`
- **Update** `app/brokers/snaptrade/__init__.py`: add `BrokerOptionsService` and `decode_osi` to exports

### 1B. Create `BrokerCredentials` dataclass

**New file**: `app/brokers/snaptrade/credentials.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BrokerCredentials:
    user_id: str
    user_secret: str
    account_id: str
```

Export from `app/brokers/snaptrade/__init__.py`.

---

## Phase 2: Database Layer

### 2A. Update `User` model (`app/db/core/models/user_data_models.py`)

Replace lines 26-28:
```python
# Before
broker = Column(String, nullable=True)
broker_account_id = Column(String, nullable=True, unique=True, index=True)

# After
broker = Column(String, nullable=True, default='snaptrade')
snaptrade_user_id = Column(String, nullable=True, unique=True, index=True)
snaptrade_user_secret = Column(String, nullable=True)
snaptrade_account_id = Column(String, nullable=True, index=True)
```

### 2B. Update `TradeProposal` model (same file)

- Line 188: Update comment from "Alpaca broker account ID" to "Brokerage account ID"
- Line 213: Rename `alpaca_order_id` → `broker_order_id`

### 2C. Create Alembic migration

**New file**: `app/db/alembic_migration/versions/user_data/<hash>_snaptrade_migration.py`
- `down_revision = 'a2b3c4d5e6f7'` (latest user_data migration)
- Add 3 columns: `snaptrade_user_id`, `snaptrade_user_secret`, `snaptrade_account_id`
- Copy `broker_account_id` data → `snaptrade_account_id` (preserve existing data)
- Drop `broker_account_id` column
- Rename `alpaca_order_id` → `broker_order_id` on `trade_proposals`

---

## Phase 3: Repository Layer

### 3A. Rewrite `app/repositories/user/broker.py`

- Change `get_broker()` singleton: import `SnapTradeBroker` instead of `ProphitBroker`
- Replace `resolve_broker_account()` → `resolve_broker_credentials()` returning `BrokerCredentials`
- Queries `User.snaptrade_user_id`, `.snaptrade_user_secret`, `.snaptrade_account_id`

### 3B. Rewrite `app/repositories/user/account.py`

- **Delete** `create_user_with_broker_account()` (no more KYC)
- Update `get_broker_account()`: use `resolve_broker_credentials()` → `broker.get_account_details(creds.user_id, creds.user_secret, creds.account_id)`
- Update `get_buying_power()`, `get_cash_balance()`, `get_equity()`: derive from `broker.get_balances()`
- Update `get_account_activities()`: use `broker.get_account_activities()`
- Add `register_snaptrade_user(clerk_id)` — calls `broker.register_user()`, stores credentials in User row
- Add `set_primary_account(clerk_id, account_id)` — updates `User.snaptrade_account_id`

### 3C. Rewrite `app/repositories/user/trading.py`

Every function: resolve `BrokerCredentials`, pass triple to SnapTrade methods.

**Parameter mapping** (Alpaca → SnapTrade):
| Alpaca | SnapTrade |
|--------|-----------|
| `qty` | `units` |
| `limit_price` | `price` + `order_type="Limit"` |
| `stop_price` | `stop` + `order_type="Stop"` |
| `time_in_force` "day" | "Day" (capitalize) |

**Drop**: `trail_price`, `trail_percent`, `take_profit`, `stop_loss`, `stop_loss_limit`, `order_class` (SnapTrade doesn't support bracket/OCO/trailing)

**Implement `close_position()`**: fetch positions → find symbol → sell full/partial qty
**Implement `close_all_positions()`**: iterate all positions → sell each
**Implement `cancel_all_orders()`**: fetch open orders → cancel each

### 3D. Delete `app/repositories/user/funding.py`

### 3E. Update `app/repositories/user/portfolio.py`

- `get_portfolio_history()`: convert `period` param to `start_date`/`end_date` → call `broker.get_performance_report()`

### 3F. Update `app/repositories/user/trade_proposal.py`

- `_proposal_to_dict()`: rename key `alpaca_order_id` → `broker_order_id`
- `_execute_trade()`: add `user_id`, `user_secret` to kwargs, map `qty`→`units`, capitalize `time_in_force`, use SnapTrade `buy()`/`sell()` signature
- `_execute_close_position()`: implement as sell order (fetch position qty, place sell)
- `approve_proposal()`: resolve SnapTrade creds from `proposal.user_id`, update `proposal.broker_order_id` field

### 3G. Update `app/repositories/user/__init__.py`

- Remove `create_user_with_broker_account` import
- Remove entire funding section (lines 37-46)
- Add new exports: `register_snaptrade_user`, `set_primary_account`

### 3H. Update `app/repositories/options.py`

- Line 5: change import to `from app.brokers.snaptrade.options import decode_osi`

---

## Phase 4: Controller Layer

### 4A. Trim `app/api/controller/broker/account.py`

- **Delete** `create_broker_account_controller` and all ACH/funding/transfer controllers
- **Keep** `get_broker_account_controller`, `get_buying_power_controller`, `get_cash_balance_controller`, `get_equity_controller`, `get_account_activities_controller`

### 4B. Create `app/api/controller/broker/connection.py` (NEW)

New controllers:
- `register_snaptrade_controller(clerk_id)` — register user with SnapTrade
- `connect_brokerage_controller(clerk_id, broker?, redirect_url?)` — generate OAuth connection URL
- `list_connections_controller(clerk_id)` — list connected brokerages
- `list_accounts_controller(clerk_id)` — list all brokerage accounts
- `set_primary_account_controller(clerk_id, account_id)` — set primary account
- `get_performance_controller(clerk_id, start_date, end_date)` — performance report

### 4C. Update `app/api/controller/broker/__init__.py`

Remove funding exports, add connection controller exports.

---

## Phase 5: API Routes

### 5A. Rewrite `app/api/routes/broker_router.py`

**Remove** (~13 endpoints):
- `POST /broker/account` (KYC account creation)
- `POST/GET/DELETE /broker/ach` (ACH bank linking)
- `POST /broker/transfers/deposit`, `withdraw`, `instant-deposit`
- `GET /broker/transfers`, `DELETE /broker/transfers/{id}`

**Remove request models**: `CreateBrokerAccountRequest`, `LinkBankRequest`, `TransferRequest`, `InstantTransferRequest`

**Add** (~6 endpoints):
- `POST /broker/register` — register with SnapTrade
- `POST /broker/connect` — get brokerage connection URL
- `GET /broker/connections` — list connections
- `GET /broker/accounts` — list accounts
- `POST /broker/accounts/primary` — set primary account
- `GET /broker/performance` — performance report

**Simplify `OrderRequest`**: Remove `trailPrice`, `trailPercent`, `takeProfit`, `stopLoss`, `stopLossLimit`, `orderClass`. Add `orderType` (Market/Limit/Stop/StopLimit).

**Keep** all order, position, and existing account-info endpoints unchanged.

---

## Phase 6: Agent Tools

### 6A. Rename `app/core/atlas/tools/alpaca/` → `app/core/atlas/tools/broker/`

### 6B. Rewrite `broker/account.py`

- `account_info(user_id, user_secret, account_id)`: use `SnapTradeBroker` → `get_account_details()` + `get_balances()`
- `account_activities(user_id, user_secret, account_id, activity_type)`: use `get_account_activities()`

### 6C. Rewrite `broker/portfolio.py`

- `get_position(user_id, user_secret, account_id, symbol)`: get all positions, filter by symbol
- `get_positions(user_id, user_secret, account_id)`: `broker.get_positions()`
- `close_position(user_id, account_id, symbol, ...)`: stays as proposal creation (broker-agnostic)
- `get_portfolio_history(user_id, user_secret, account_id, ...)`: use `broker.get_performance_report()`
- Remove `_get_trade_dates()` helper (Alpaca-specific)

### 6D. Rewrite `broker/trade.py`

- `propose_trade(...)`: no broker change needed (creates DB proposal)
- `get_orders(user_id, user_secret, account_id, status)`: `broker.get_orders()`
- `cancel_order(user_id, user_secret, account_id, order_id)`: `broker.cancel_order()`
- `cancel_all_orders(user_id, user_secret, account_id)`: get open orders → cancel each
- `get_asset(symbol)`: **Remove** (Alpaca-specific, no SnapTrade equivalent)

### 6E. Update tool registries

- `app/core/atlas/tools/chat_registry.py`: update imports from `tools.alpaca` → `tools.broker`, remove `get_asset`
- `app/core/atlas/tools/worker_agent/setup.py`: same import update

---

## Phase 7: Chat Session (Agent Context Injection)

### 7A. Update `app/services/shared/chat_executor.py` (lines 84-107)

```python
# Before: resolve_broker_account → inject broker_account_id
# After: resolve_broker_credentials → inject user_id, user_secret, account_id
```

Change import from `resolve_broker_account` → `resolve_broker_credentials`, inject all three SnapTrade credentials into the system prompt broker context.

---

## Phase 8: Deletion & Cleanup

### 8A. Delete directories
- `app/brokers/alpaca/` (entire directory)
- `app/brokers/alpaca_broker/` (entire directory)
- `.claude/skills/fund-firm/` (funding no longer exists)

### 8B. Delete files
- `app/repositories/user/funding.py`
- `tests/brokers/test_alpaca_broker.py`

### 8C. Update references
- `app/api/controller/user.py`: `brokerAccountId` → `snaptradeAccountId`
- `.claude/skills/agent-tool/references/tool-patterns.md`: update `ProphitBroker` → `SnapTradeBroker`
- `requirements.txt`: keep `alpaca-py` (still used for options data), already added `snaptrade-python-sdk`

### 8D. Update `SNAPTRADE.md`
- Remove references to `app/brokers/alpaca_broker/`
- Document the full integration architecture (routes → controllers → repos → SnapTradeBroker)

---

## Verification

1. **Alembic migration**: `alembic upgrade head` succeeds on user_data DB
2. **SnapTrade tests**: `python -m pytest tests/brokers/test_snaptrade_broker.py -v` passes
3. **Import check**: `python -c "from app.brokers.snaptrade import SnapTradeBroker; print('OK')"` succeeds
4. **No Alpaca imports remain**: `grep -r "from app.brokers.alpaca" app/` returns no results
5. **API startup**: FastAPI app starts without import errors
6. **Manual test**: Use `t.py` to verify `broker.get_account_details()`, `broker.get_positions()`, `broker.buy()` work with SnapTrade credentials

---

## Files Summary

| Action | Files |
|--------|-------|
| **New** | `snaptrade/options.py`, `snaptrade/credentials.py`, `broker/connection.py` controller, alembic migration |
| **Rewrite** | `broker.py` repo, `account.py` repo, `trading.py` repo, `trade_proposal.py` repo, `portfolio.py` repo, `broker_router.py`, `account.py` controller, agent tools (3 files), `chat_executor.py` |
| **Delete** | `app/brokers/alpaca/`, `app/brokers/alpaca_broker/`, `funding.py` repo, `fund-firm` skill, `test_alpaca_broker.py` |
| **Update** | `user_data_models.py`, `__init__.py` files (3), `options.py` repo, `chat_registry.py`, `worker_agent/setup.py`, `tool-patterns.md`, `controller/user.py` |
