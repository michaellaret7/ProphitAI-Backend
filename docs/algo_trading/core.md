# Core Contracts

Every stage in the pipeline exchanges one of three types, over the shared `AlgorithmContext` snapshot.  Everything in `core/` is contract — no business logic lives here.

## `Insight` — alpha output

`core/models.py` — frozen dataclass, produced by `AlphaModel.update()`.

```python
@dataclass(frozen=True)
class Insight:
    symbol: str
    direction: int           # -1 / 0 / +1  (NOT the Direction enum — that has no flat)
    generated_time: datetime
    close_time: datetime     # when the prediction expires
    magnitude: float | None = None     # expected return, z-score, whatever
    confidence: float | None = None    # 0..1 hint
    weight: float | None = None        # relative weight hint vs. alpha's other insights
    source_alpha: str = ""   # MUST match the alpha's `name` — PCMs partition on this
```

### Direction

**Use int (`-1 / 0 / +1`)**, not the `Direction` enum.  `Direction` is LONG/SHORT only and has no flat state; `Insight.direction` needs flat.

### Magnitude

Not standardized across alphas — can be expected return, z-score, Donchian position.  `MultiAlphaBlender` cross-sectionally z-scores magnitude per-alpha before blending, so an alpha can emit whatever unit it wants natively.

### `source_alpha`

Must match the alpha's `name` attribute.  Multi-alpha PCMs partition the insight list by this field to z-score each alpha's cohort independently.  The three built-in bases (`PerSymbolAlpha` / `CrossSectionalAlpha` / `PairAlpha`) set it from `self.name` automatically.

## `PortfolioTarget` — PCM / risk output

`core/models.py` — frozen dataclass.

```python
@dataclass(frozen=True)
class PortfolioTarget:
    symbol: str
    target_shares: float     # signed: positive = long, negative = short, 0 = close
```

### Rules

- `target_shares` is signed.  **0.0 means "flatten this symbol"** — the execution stage diffs against the current position and closes it.
- Shares are `float`.  Alpaca supports fractional shares natively; integer sizes happen in execution, not here.
- **Symbols not in the target list are "no target"** — not "flatten".  Existing positions stay as-is unless you emit `target_shares=0.0`.  Built-in PCMs call `append_close_orphans` to close positions no longer wanted.

### Weight → shares

PCMs think in percentages.  Use `portfolio_construction.helpers.weight_to_shares` so every PCM converts identically:

```python
target_shares = (equity * weight * direction) / price
```

## `AlgorithmContext` — per-bar state

`core/models.py` — dataclass, rebuilt every bar by the engine.

```python
@dataclass
class AlgorithmContext:
    timestamp: datetime                      # current bar timestamp
    portfolio: Portfolio                     # mutable — Execution writes here
    data: dict[str, pd.DataFrame]            # per-ticker OHLCV up to current bar
    warmup: bool = False                     # True during alpha warmup period
    market: MarketDataView | None = None     # optional fast NumPy view
```

### `data`

Keyed by ticker.  Each value is the **full history up to and including** the current bar, NOT just the current row.  This means:

- Slice off `df.iloc[-self.lookback:]` to get your window.
- The last row is always the current bar; `df["close"].iloc[-1]` is the latest close.
- Engines build this by pre-filtering each ticker's full DataFrame at every bar.

### `portfolio`

The **only mutable** attribute.  Alphas / PCMs / risk should treat it as read-only; only `ExecutionModel` (via `PortfolioSink` / `BrokerSink`) mutates it.

Useful reads:
- `ctx.portfolio.equity()` — mark-to-market equity.
- `ctx.portfolio.positions` — `{symbol: Position}` for currently held symbols.
- `ctx.portfolio.get_position(symbol)` — `+1 / -1 / 0`.
- `ctx.portfolio.cash`.

### `warmup`

True for the first `algorithm.max_lookback` bars.  Alphas still tick (they need to build state), but `ExecutionModel.execute` early-returns while warm.  Alphas should NOT special-case warmup — just emit normally; orders get suppressed downstream.

### `market` (optional, advanced)

`MarketDataView` is a zero-copy NumPy view over the same data.  Useful for high-frequency signals where pandas slicing is a bottleneck:

```python
close_arr = ctx.market.window("AAPL", "close", lookback=20)   # np.ndarray
latest = ctx.market.latest("AAPL", "close")                    # float or None
```

Not required — stick with `ctx.data` unless profiling shows pandas as the hotspot.

## Protocols (stage contracts)

`core/protocols.py` — five `Protocol` classes.  Duck-typed, `@runtime_checkable`.

### `AlphaModel`

```python
class AlphaModel(Protocol):
    name: str           # unique — PCMs partition on this
    lookback: int       # bars required before update() emits useful insights

    def update(self, ctx: AlgorithmContext) -> list[Insight]: ...
```

Don't implement this directly — subclass one of the three bases in `alphas/base.py`.  See `alphas.md`.

### `PortfolioConstructor`

```python
class PortfolioConstructor(Protocol):
    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]: ...
```

Owns rebalance cadence, weight scheme, and position caps.

### `RiskManagementModel`

```python
class RiskManagementModel(Protocol):
    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]: ...
```

Every concrete `RiskRule` (stops, trails, cooldowns, limits, windows) is itself a full `RiskManagementModel`.  Compose multiple via `CompositeRiskModel`.

### `ExecutionModel`

```python
class ExecutionModel(Protocol):
    def execute(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> None: ...
```

Pure side-effect stage.  The built-in `execution.ExecutionModel` class is usually all you need — parameterize it with a sink, not a subclass.

### `LifecycleAwareRiskModel` (optional)

```python
class LifecycleAwareRiskModel(Protocol):
    def on_position_opened(self, ctx: AlgorithmContext, symbol: str) -> None: ...
    def on_position_closed(self, ctx: AlgorithmContext, symbol: str, pnl: float) -> None: ...
```

Risk rules that track lifecycle state (trailing stops, time stops, consecutive-loss cooldowns) implement this structurally.  The engine gates calls with `isinstance(risk, LifecycleAwareRiskModel)` per step.

## `Direction` enum

`core/enums.py` — used only for broker-side code (`BrokerPositionSnapshot`), not for Insights.

```python
class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
```
