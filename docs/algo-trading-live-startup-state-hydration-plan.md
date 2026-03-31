# Algo Trading Live Startup State Hydration Plan

## Purpose

This document defines how to add portfolio statefulness to the live algo trading engine so that a restarted live strategy does not come up assuming a flat book.

The core requirement is simple:

- When the live strategy process starts, it must load the current portfolio state from the broker before it begins processing live bars.
- That broker state must become the initial in-memory state for the live engine.
- The engine must then trade from that hydrated state instead of behaving as if no positions exist.

This solves the current failure mode where restarting a live strategy can cause duplicate entries, incorrect available cash calculations, and position-cap errors because the engine starts from scratch in memory.

## Explicit Scope

This feature is for live and paper trading only.

It is not for backtesting.

That distinction is non-negotiable.

### In Scope

- Hydrating the live engine from Alpaca at process startup.
- Preventing duplicate same-direction entries after restart.
- Restoring correct cash, equity baseline, position count, and symbol-level direction state for the live engine.
- Failing fast on unsafe startup conditions such as unmanaged positions or ambiguous open orders.

### Out of Scope for V1

- Backtest startup hydration.
- Generic persistence for all engine state.
- Exact reconstruction of every risk-control internal variable across restarts.
- Rebuilding historical trade logs from broker fills.
- Broker abstraction layers or protocols (Alpaca is the only broker).

## Why This Is Needed

The current live engine startup path is stateless.

At startup, the live engine:

- creates a new `PortfolioTracker`
- creates fresh per-symbol `PositionTracker`s
- initializes tracker cash from broker equity
- does not load broker positions into tracker state
- does not load open orders into startup validation

That means the process restarts with memory that says:

- no positions are open
- all capital is free cash
- all symbols are flat

That is wrong whenever the broker account already has open positions.

## Core Design

### High-Level Rule

The live engine will always follow this sequence:

1. warm up market data
2. fetch the startup snapshot from Alpaca
3. validate the snapshot against the configured live universe
4. hydrate in-memory portfolio state from the snapshot
5. start processing live bars

The engine must never subscribe to live bars before startup hydration completes successfully.

### Startup Snapshot Models

The startup snapshot will be a set of dataclasses containing only the fields the engine actually needs.

```python
from dataclasses import dataclass, field
from datetime import datetime

from prophitai_algo_trading.execution.models import Direction


@dataclass
class BrokerPositionSnapshot:
    symbol: str
    shares: float
    direction: Direction
    entry_price: float


@dataclass
class BrokerOrderSnapshot:
    order_id: str
    symbol: str
    side: str
    qty: float | None
    status: str
    order_type: str


@dataclass
class BrokerStartupSnapshot:
    cash: float
    equity: float
    positions: list[BrokerPositionSnapshot] = field(default_factory=list)
    open_orders: list[BrokerOrderSnapshot] = field(default_factory=list)
    captured_at: datetime | None = None


@dataclass
class HydrationSummary:
    cash: float
    equity: float
    hydrated_count: int
    hydrated_symbols: list[str]
    unmanaged_symbols: list[str]
    open_order_count: int
    success: bool
```

## Startup Behavior Contract

### Required Live Startup Invariants

After hydration and before the first live bar:

- `PortfolioTracker.cash` must equal broker cash, not broker equity.
- `PortfolioTracker` must contain an open position for every broker position the engine is responsible for.
- Each symbol's `PositionTracker` must reflect the broker direction for that symbol.
- `PortfolioTracker.open_position_count` must match the number of hydrated managed positions.
- Entry sizing and max-position gating must operate from this hydrated state.

### Managed vs Unmanaged Positions

At startup, broker positions must be partitioned into:

- managed positions: symbols that are in the configured live universe and successfully warmed up
- unmanaged positions: symbols not in the configured live universe or symbols the live engine cannot safely manage

V1 policy: always fail fast if unmanaged positions exist.

Reason:

- silently ignoring unmanaged broker positions is unsafe
- silently tracking them read-only still leaves unclear ownership
- failing fast makes the problem visible and prevents accidental overtrading

### Open Orders Policy

The startup snapshot must also include open orders.

V1 policy: always fail fast if the broker account contains open orders for managed symbols.

Reason:

- open entry orders can still duplicate exposure after restart
- open exit orders can conflict with the engine's assumptions
- correct reconciliation of partial fills and pending orders is more complex than position hydration alone

This is the safest first implementation.

## Backtesting Boundary

This feature must not alter backtesting behavior.

Backtest engines must continue to:

- start flat
- use explicit `initial_capital`
- avoid broker APIs entirely
- avoid startup snapshots entirely

That means:

- no snapshot-loading logic in backtest engines
- no hidden default hydration inside `PortfolioTracker`
- no conditional branch that changes backtest startup semantics

The live path may hydrate.

The backtest path may not.

## File-by-File Implementation Plan

### 1. `packages/algo_trading/src/prophitai_algo_trading/broker/models.py`

Create a new module for the startup snapshot dataclasses.

Planned contents:

- `BrokerPositionSnapshot`
- `BrokerOrderSnapshot`
- `BrokerStartupSnapshot`
- `HydrationSummary`

Responsibilities:

- represent startup broker state in a normalized form
- provide a typed reconciliation result

### 2. `packages/algo_trading/src/prophitai_algo_trading/broker/portfolio.py`

This remains the Alpaca-specific data retrieval layer.

Changes planned:

- add private normalization helpers that convert Alpaca account, positions, and orders into snapshot models
- add a method that assembles a full startup snapshot from:
  - account
  - positions
  - open orders

Specific responsibilities:

- normalize Alpaca long/short side into internal `Direction`
- normalize quantities into floats
- normalize average entry price into `entry_price`
- normalize order metadata into the minimal startup order shape

Things this file should not do:

- no live-engine reconciliation logic
- no portfolio-tracker mutation
- no startup policy decisions about managed vs unmanaged positions

Those decisions belong in the live engine layer, not in the data retrieval layer.

### 3. `packages/algo_trading/src/prophitai_algo_trading/broker/alpaca.py`

This file will expose the startup snapshot through the `Alpaca` facade.

Changes planned:

- add `get_startup_snapshot() -> BrokerStartupSnapshot`
- delegates to `AlpacaPortfolio` for the actual data fetching and normalization

Purpose:

- keep `LiveRunner` from needing to call `self._broker.portfolio.get_account()`, `self._broker.portfolio.get_positions()`, and `self._broker.portfolio.get_orders()` separately
- make startup reconciliation a single broker call from the live engine's perspective

### 4. `packages/algo_trading/src/prophitai_algo_trading/broker/__init__.py`

Export the new models alongside `Alpaca`:

- `BrokerStartupSnapshot`
- `BrokerPositionSnapshot`
- `BrokerOrderSnapshot`
- `HydrationSummary`

Small cleanup step, not a core behavior change.

### 5. `packages/algo_trading/src/prophitai_algo_trading/execution/portfolio_tracker.py`

This file needs explicit hydration APIs.

Current issue:

- the constructor assumes `cash == initial_capital`
- that is valid for backtests and flat starts
- that is invalid for a live broker account that already has open positions

Required changes:

- keep the constructor default behavior unchanged
- add explicit seed methods that are only called by the live startup path

Suggested methods:

```python
def seed_cash(self, cash: float) -> None: ...
def seed_position(
    self,
    symbol: str,
    shares: float,
    direction: Direction,
    entry_price: float,
    entry_date: datetime,
    entry_commission: float = 0.0,
) -> None: ...
def seed_latest_prices(self, prices: dict[str, float]) -> None: ...
```

Expected behavior:

- `initial_capital` may still be seeded from broker equity for baseline equity tracking
- `cash` must then be explicitly overwritten with broker cash
- seeded positions must populate `_positions`
- seeded prices must populate `_latest_prices`

Important design rule:

- do not make the constructor auto-hydrate
- do not add broker calls here
- keep the class reusable for backtests

### 6. `packages/algo_trading/src/prophitai_algo_trading/execution/position_tracker.py`

This file needs a simple explicit hydration method.

Current issue:

- `PositionTracker` starts with `position = 0` every time
- that is correct for backtests
- that is wrong for live restart when the broker already has an open position

Required change:

- add a method to seed the current position state directly

```python
def hydrate(self, position: int) -> None:
    if position not in (-1, 0, 1):
        raise ValueError(...)
    self.position = position
```

Note on tracker responsibilities:

- `PositionTracker` owns direction state (`position` as -1, 0, 1)
- `PortfolioTracker` owns share count via `PositionState` in `_positions`
- both must be hydrated consistently by the reconciliation layer

### 7. `packages/algo_trading/src/prophitai_algo_trading/engines/live_reconciliation.py`

Create a new helper module for live startup hydration.

Reason this should be a separate file:

- startup policy is easier to test if extracted
- it keeps the orchestration code isolated from the streaming loop

Planned responsibilities:

- validate startup snapshot
- partition managed vs unmanaged positions
- validate open orders
- map broker positions onto tracker state
- produce a `HydrationSummary` for logging
- apply normalized startup state to:
  - `PortfolioTracker`
  - per-symbol `PositionTracker`s

Suggested helper functions:

```python
def partition_positions(
    positions: list[BrokerPositionSnapshot],
    active_universe: list[str],
) -> tuple[list[BrokerPositionSnapshot], list[BrokerPositionSnapshot]]: ...

def validate_open_orders(
    orders: list[BrokerOrderSnapshot],
    active_universe: list[str],
) -> None: ...

def hydrate_live_state(
    snapshot: BrokerStartupSnapshot,
    portfolio_tracker: PortfolioTracker,
    position_trackers: dict[str, PositionTracker],
    latest_prices: dict[str, float],
    active_universe: list[str],
) -> HydrationSummary: ...
```

This module should not:

- fetch broker data
- subscribe to live bars
- execute trades

It should only reconcile and apply startup state.

### 8. `packages/algo_trading/src/prophitai_algo_trading/engines/live.py`

This is the main orchestration change.

Planned updates:

- warm up data first
- fetch `snapshot = self._broker.get_startup_snapshot()`
- create the `PortfolioTracker`
- run the reconciliation helper
- only then start the live subscription loop

Startup order should be:

1. `await self.warmup()`
2. `snapshot = self._broker.get_startup_snapshot()`
3. build `PortfolioTracker(initial_capital=snapshot.equity, ...)`
4. call `hydrate_live_state(...)`
5. log hydration summary
6. start `async for bar in async_subscribe(...)`

Why warmup comes first:

- warmup determines the active universe
- warmup fills `_latest_prices`
- the reconciliation layer may use those prices for mark-to-market and diagnostics
- a position in an unwarmable symbol should be treated as an unsafe startup condition

Failure handling:

- if `get_startup_snapshot()` fails (network error, auth failure, Alpaca downtime), the engine must not start — hard failure with clear logging
- if reconciliation raises (unmanaged positions, open orders, bad data), the engine must not start — hard failure with clear logging

### 9. `packages/algo_trading/src/prophitai_algo_trading/main.py`

This file may need only a small wiring change.

If `LiveRunner` defaults are clean, this file may require little or no modification.

### 10. `packages/algo_trading/tests/test_portfolio_tracker.py`

Extend this file instead of creating unnecessary duplicate tracker tests.

Add tests for:

- seeding broker cash after tracker construction
- seeding hydrated long positions
- seeding hydrated short positions
- correct total equity after hydration
- correct open-position count after hydration

These tests should validate the accounting layer independently of `LiveRunner`.

### 11. `packages/algo_trading/tests/test_engine_startup_state.py`

Add one focused engine-level test file for startup hydration behavior.

This file should cover:

- live startup hydrates a pre-existing long
- live startup hydrates a pre-existing short
- same-direction duplicate entry is suppressed after hydration
- unmanaged positions raise a startup error
- open orders raise a startup error
- backtest engines still start flat

Test strategy:

- use a lightweight fake `Alpaca` class that returns canned snapshots
- do not use a mocking framework
- keep the test explicit and concrete

## Risk Control Treatment

### V1 Policy

Do not attempt exact restart continuity for all risk controls in V1.

Reason:

- some controls store broker-independent internal state
- trailing stops track high-water or low-water marks
- time stops track bars held
- cooldowns track post-exit timing

Broker positions alone do not contain enough information to reconstruct all of that exactly.

### What V1 Does Restore

V1 restores:

- open positions
- direction
- shares
- entry price
- cash
- equity baseline

### What V1 Does Not Restore Exactly

V1 does not restore:

- trailing stop anchors
- holding-bar counters
- cooldown counters
- any control-local hidden state not represented in the startup snapshot

This is acceptable for V1 because the primary objective is to prevent duplicate position creation after restart.

If exact risk continuity is required later, that should be a Phase 2 feature with explicit persisted engine-state snapshots.

## Entry Date Policy for Hydrated Positions

The current execution model requires an `entry_date` in `PositionState`.

The broker startup snapshot does not necessarily provide the true historical fill timestamp for the open position.

V1 policy:

- seed `entry_date` with `snapshot.captured_at` or current startup time

This is intentionally conservative and honest in effect:

- the live engine knows the position exists
- direction and sizing behavior become correct
- time-based controls are not pretending to know the original hold duration

This should be documented clearly in code comments.

## Failure Policy

Startup should fail fast when the engine cannot safely reconcile live state.

V1 startup failures:

- unmanaged broker positions
- open orders for managed symbols
- broker connectivity failure (network, auth, Alpaca downtime)
- malformed broker snapshot data
- inconsistent symbol direction or quantity data
- empty active universe after warmup

Failing fast is the correct behavior.

Silent partial reconciliation is dangerous.

## Logging and Diagnostics

The startup process should emit a structured summary that includes:

- broker cash
- broker equity
- number of hydrated positions
- list of hydrated symbols
- list of unmanaged symbols, if any
- count of open orders
- whether startup hydration succeeded

Example summary:

```text
Live startup reconciliation complete
cash=124532.41
equity=141990.27
hydrated_positions=3
symbols=AAPL,MSFT,NVDA
open_orders=0
```

This is important because the operator needs immediate visibility into what the engine believes it loaded.

## Acceptance Criteria

The feature is complete when all of the following are true:

1. A live restart with existing broker positions hydrates those positions before the first live bar is processed.
2. The live engine no longer assumes all broker equity is free cash.
3. The live engine no longer attempts duplicate same-direction entries immediately after restart.
4. Position-count limits reflect already-open broker positions.
5. Backtest engines remain flat-start and unchanged.
6. Unsafe startup states fail fast with clear errors.

## Implementation Order

This should be implemented in the following order:

1. write the startup snapshot models in `broker/models.py`
2. implement Alpaca snapshot assembly in `portfolio.py` and expose via `alpaca.py`
3. add explicit hydration APIs to the execution trackers
4. implement the live reconciliation helper
5. wire the live engine to use the helper
6. add tracker-level tests
7. add engine-level startup tests
8. manually validate the behavior in a paper account

That order keeps the dependency chain clean and avoids mixing orchestration with data-shape design too early.

## Manual Validation Plan

After code changes are complete, validate in paper trading with this exact flow:

1. open one or more paper positions in Alpaca
2. stop the live process
3. restart the live process
4. confirm startup logs show the hydrated symbols
5. confirm the engine does not open duplicate same-direction entries for those symbols
6. confirm position count and sizing reflect the existing positions
7. confirm a legitimate exit signal can still close a hydrated position

This manual validation is important because startup reconciliation is fundamentally a live-system concern.

## Future Phase 2

If needed later, Phase 2 can add:

- exact restart continuity for stateful risk controls via persisted engine-state snapshots
- explicit control-level rehydration hooks
- reconciliation between persisted engine state and broker truth
- broker abstraction layer if a second broker becomes necessary

That is a separate feature and should not be folded into V1.

## Final Implementation Rule

The implementation must preserve this simple rule:

- live engines may hydrate from a startup snapshot
- backtest engines may not

If any code change weakens that boundary, the design is wrong.
