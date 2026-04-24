# Risk Management

Risk runs after PCM and before Execution.  It can modify, zero, or drop any target.  Every concrete risk component is a full `RiskManagementModel` — drop it straight into `Algorithm(risk_management=...)` or stack several via `CompositeRiskModel`.

## Protocol

```python
class RiskManagementModel(Protocol):
    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]: ...
```

Typical operations:

- Scale all targets by a delever factor during drawdown.
- Zero targets that breach a sector cap or gross limit.
- Force-close a position when a stop fires.
- Veto new entries during a cooldown.

## Two shapes of risk component

### 1. `RiskRule` subclasses — per-symbol hooks

Base: `risk/base.py::RiskRule`.  Subclass and override whichever hooks you need:

| Hook | When fires | What it does |
|------|-----------|--------------|
| `block_entry(ctx)` | Before any new-entry target | Return `True` to veto the entry |
| `force_exit(ctx)` | Per invested symbol per bar | Return `True` to force-close |
| `on_bar(ctx)` | Per invested symbol per bar (refresh pass) | Update internal state (e.g. trailing high-water mark) |
| `on_entry(ctx)` | After a position opens | Initialize per-symbol state |
| `on_exit(ctx, trade_pnl)` | After a position closes | Tear down per-symbol state; update streaks |

All hooks take a `RiskContext` (not `AlgorithmContext` — see below).  Default implementations are no-ops; override only what you need.

#### `RiskContext` (per-rule input)

```python
@dataclass
class RiskContext:
    symbol: str
    price: float                       # current bar close
    timestamp: datetime
    df: pd.DataFrame                   # per-symbol history
    current_position: int              # +1 / -1 / 0
    entry_price: float | None          # None if flat
    entry_time: datetime | None        # None if flat
    proposed_direction: int | None     # only set during block_entry
    portfolio_equity: float
    portfolio_peak: float               # running peak for drawdown rules
```

#### `RiskRule.manage()` — what the base does for you

`RiskRule` already implements `manage()`; you never override it.  Per call:

1. Update the rule's own `PeakEquityTracker` with current equity.
2. Fire `on_bar` for every invested symbol (or once with a probe if flat).
3. Collect `force_exit` hits across invested symbols.
4. For each incoming target:
   - If it's a new entry and `block_entry` fires → drop it.
   - If the symbol is in `force_exit` → override with `target_shares=0.0`.
   - Otherwise pass through.
5. Append zero-share targets for forced-exit symbols not already in the target list.

`on_position_opened` / `on_position_closed` (satisfying `LifecycleAwareRiskModel`) forward into `on_entry` / `on_exit`.

### 2. Standalone `RiskManagementModel` — target-list transforms

When the per-symbol hook shape doesn't fit (proportional scaling, list-wide computations), write a plain class implementing `manage()` directly.  `MaxDrawdownRiskModel` and `MaxGrossExposureRiskModel` are built-ins of this shape.

## Built-in rules

### Exits (`risk/stops.py`)

All four are `RiskRule`s; drop straight into `CompositeRiskModel`.

| Rule | Fires when | Notes |
|------|-----------|-------|
| `StopLossExit(pct)` | Price moves `pct` against the position from entry | `pct=0.05` = 5% adverse move |
| `TrailingStopExit(pct)` | Price retraces `pct` from favorable extreme since entry | Tracks per-symbol high/low water mark via `on_bar` |
| `ProfitTargetExit(pct)` | Price moves `pct` favorable from entry | — |
| `TimeStop(max_bars=..., max_duration=...)` | Held > `max_bars` bars OR wall-clock > `max_duration` | Exactly one of the two is required |

### Cooldowns (`risk/cooldowns.py`)

| Rule | Behavior |
|------|----------|
| `ReentryCooldown(bars)` | Block new entries on a symbol for `bars` bars after its last exit |
| `ConsecutiveLossCooldown(max_losses, bars)` | Block entries across ALL symbols for `bars` bars after `max_losses` consecutive losing trades |

### Portfolio limits (`risk/limits.py`)

| Rule | Behavior |
|------|----------|
| `DailyLossLimit(loss_pct)` | Block entries once today's equity drop exceeds `loss_pct` of day-start equity.  Resets at UTC midnight. |
| `PortfolioDrawdownLimit(dd_pct)` | Block entries once drawdown from running peak exceeds `dd_pct` |

### Windows (`risk/windows.py`)

| Rule | Behavior |
|------|----------|
| `TradingWindow(start, end)` | Block entries outside a `datetime.time` window.  Uses bar timestamp's time-of-day directly — no TZ conversion. |

### Target-list transforms (standalone)

#### `MaxDrawdownRiskModel`

Peak-to-trough circuit breaker with **delever + cooldown**, NOT a permanent halt:

```python
MaxDrawdownRiskModel(
    max_drawdown_pct=0.15,      # breach threshold
    delever_factor=0.5,         # multiply every target's shares during cooldown
    cooldown_days=30,           # delever duration
)
```

On cooldown expiry the peak resets to current equity so an underwater strategy doesn't re-trigger forever.

#### `MaxGrossExposureRiskModel`

Final guard — proportional downscaling so `sum(|shares| * price) ≤ max_gross * equity`:

```python
MaxGrossExposureRiskModel(max_gross=1.5)
```

Run this **last** in a composite so every upstream adjustment is respected.

## Composition — `CompositeRiskModel`

Stack multiple rules.  **Order matters**: portfolio-wide circuit breakers first, position-level stops next, gross guard last.

```python
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    MaxDrawdownRiskModel,
    DailyLossLimit,
    StopLossExit,
    MaxGrossExposureRiskModel,
)

risk = CompositeRiskModel([
    MaxDrawdownRiskModel(max_drawdown_pct=0.15, delever_factor=0.5),  # portfolio delever
    DailyLossLimit(loss_pct=0.03),                                    # portfolio-wide block
    StopLossExit(pct=0.05),                                           # per-symbol exits
    MaxGrossExposureRiskModel(max_gross=1.5),                         # final gross cap
])
```

`CompositeRiskModel`:

- Runs children in sequence, each sees the previous child's output.
- Forwards lifecycle events to every child structurally satisfying `LifecycleAwareRiskModel`.
- Raises if given an empty list.

## Lifecycle hooks — `LifecycleAwareRiskModel`

Rules that track per-position state (trailing stops, time stops, consecutive-loss cooldowns) need `on_position_opened` / `on_position_closed` hooks.  `RiskRule` already provides them — they forward into `on_entry` / `on_exit`.

The engine gates lifecycle dispatch with `isinstance(risk, LifecycleAwareRiskModel)` once per step.  Risk models that don't need state simply skip — no method definitions, no overhead.

Every bar, `BarRunner`:

1. Snapshots pre-execute positions (`{symbol: +1/-1}`).
2. Runs `ExecutionModel.execute`.
3. Diffs pre- vs post-execute positions.
4. Fires `on_position_opened` / `on_position_closed` for each delta.
5. **Flips** (long → short or short → long in a single bar) fire BOTH hooks — the close, then the open.
6. `pnl` on `on_position_closed` comes from the `Trade` record produced during this bar.

## Writing a custom risk rule

### Example — per-symbol max-bars stop

```python
from prophitai_algo_trading.risk.base import RiskRule, RiskContext


class MaxBarsStop(RiskRule):
    def __init__(self, max_bars: int):
        super().__init__()
        self.max_bars = max_bars
        self._entry_bars: dict[str, int] = {}

    def on_entry(self, ctx: RiskContext) -> None:
        self._entry_bars[ctx.symbol] = len(ctx.df) - 1

    def on_exit(self, ctx: RiskContext, trade_pnl: float) -> None:
        self._entry_bars.pop(ctx.symbol, None)

    def force_exit(self, ctx: RiskContext) -> bool:
        if ctx.current_position == 0:
            return False

        entry_bar = self._entry_bars.get(ctx.symbol)
        if entry_bar is None:
            return False

        return (len(ctx.df) - 1) - entry_bar >= self.max_bars
```

### Example — portfolio-wide sector cap (target-list transform)

```python
from prophitai_algo_trading.core.models import AlgorithmContext, PortfolioTarget


class SectorGrossCap:
    def __init__(self, sector_of: dict[str, str], max_per_sector: float):
        self._sector_of = sector_of
        self._max = max_per_sector

    def manage(self, ctx: AlgorithmContext, targets: list[PortfolioTarget]) -> list[PortfolioTarget]:
        equity = ctx.portfolio.equity()
        if equity <= 0:
            return list(targets)

        # group by sector, compute gross per sector, scale offenders
        ...
        return scaled_targets
```

Write as a `RiskRule` when you have per-symbol state tied to entries/exits; write as a plain `manage()` class when the transformation is list-wide.

## Interaction with Execution

- Risk runs BEFORE Execution.  By the time `ExecutionModel.execute` sees targets, stops have fired, cooldowns have vetoed entries, and delever multipliers have been applied.
- Forced exits come through as `target_shares=0.0` — Execution treats that as "flatten."
- Execution respects `ctx.warmup` and no-ops during warmup — so risk rules that fire during warmup are "free" (no trades, no lifecycle events).
