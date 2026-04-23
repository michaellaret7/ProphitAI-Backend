# Algorithm Framework — Architecture Decision Record

**Status:** Proposed — 2026-04-23
**Owner:** algo_trading package
**Inspired by:** QuantConnect Lean's Algorithm Framework (2018+)

---

## Context

The current `algo_trading` package is **strategy-centric**. `BaseStrategy` couples three orthogonal concerns in one class:

1. Indicator computation (enrich OHLCV DataFrame)
2. Signal generation (emit `position` column ∈ {-1, 0, +1})
3. Implicit ranking/sizing hints (`score()` method)

This was fine when one strategy ran on one universe. It breaks for **multi-alpha portfolios**, where multiple signal producers feed a shared book. We hand-rolled this in `projects/qc_test/multi_alpha_daily/` with a `SignalCombiner` — the pattern should be native to the framework, not bolted on.

The existing `EventDrivenBacktest` and `LiveRunner` already split the per-bar loop into the right stages (collect signals → rank → size → risk-gate → fill). What's missing is the **type contract** between stages and **pluggable models** at each seam.

## Decision

Introduce a 5-stage pipeline derived from Lean's Algorithm Framework:

```
  Slice (bars + corporate actions at t)
    │
    ▼
  [UniverseSelection]         ← out of scope; static lists for now
    │
    ▼
  [AlphaModel]*               ← N alphas concat → list[Insight]
    │
    ▼
  [PortfolioConstructionModel] ← Insights → list[PortfolioTarget]
    │
    ▼
  [RiskManagementModel]        ← Targets → list[PortfolioTarget] (may modify)
    │
    ▼
  [ExecutionModel]             ← Simulated (backtest) or Broker (live)
```

Each stage is a pure function of its input. The SAME pipeline runs in backtest and live — only `ExecutionModel` differs. Multi-alpha is native: just pass multiple `AlphaModel` instances; PCM blends their insights.

## Core types

Three frozen dataclasses are the contracts between stages. Locking these first; no code depends on anything we haven't decided yet.

```python
@dataclass(frozen=True)
class Insight:
    symbol: str
    direction: int                     # -1 (down), 0 (flat), +1 (up)
    generated_time: datetime            # when this prediction was produced
    close_time: datetime                # when the prediction expires
    magnitude: float | None = None      # expected return (not standardized)
    confidence: float | None = None     # 0..1 — how sure the alpha is
    weight: float | None = None         # relative weight hint for PCM
    source_alpha: str = ""              # name of producing AlphaModel

@dataclass(frozen=True)
class PortfolioTarget:
    symbol: str
    target_shares: float                # signed; +long, -short, 0 = flat

@dataclass
class AlgorithmContext:
    """Read-only state passed to every model each bar."""
    timestamp: datetime
    portfolio: Portfolio                # existing class
    data: dict[str, pd.DataFrame]       # per-ticker history up to timestamp
    warmup: bool = False
```

### Design rationale for each type

- **`Insight.direction` as int, not Enum** — matches existing `position` convention in `BaseStrategy.compute_signals`. The existing `Direction` enum is LONG/SHORT only (no FLAT), wrong for this.
- **`PortfolioTarget` as signed shares, not percentage** — lets the PCM decide in the native unit the engine needs. Percentage helpers can be class methods later if needed.
- **`AlgorithmContext.data` as dict[str, DataFrame]** — preserves the current data layout. A richer `Slice` type is Phase 5+, not Phase 0.
- **Frozen `Insight` / `PortfolioTarget`** — pure data, safe to log, hash, and cache. Mutable `AlgorithmContext` because `Portfolio` state mutates over the bar.

## Model protocols

Each model is a Python `Protocol` — duck typing, no inheritance required.

```python
class AlphaModel(Protocol):
    name: str
    lookback: int

    def update(self, ctx: AlgorithmContext) -> list[Insight]: ...

class PortfolioConstructionModel(Protocol):
    def create_targets(
        self, ctx: AlgorithmContext, insights: list[Insight],
    ) -> list[PortfolioTarget]: ...

class RiskManagementModel(Protocol):
    def manage(
        self, ctx: AlgorithmContext, targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]: ...

class ExecutionModel(Protocol):
    def execute(
        self, ctx: AlgorithmContext, targets: list[PortfolioTarget],
    ) -> None: ...
```

The composed `Algorithm`:

```python
@dataclass
class Algorithm:
    alphas: list[AlphaModel]
    portfolio_construction: PortfolioConstructionModel
    risk_management: RiskManagementModel
    execution: ExecutionModel
```

Engines take an `Algorithm` instance and drive the pipeline each bar.

## Directory layout (≤500-line files)

```
packages/algo_trading/src/prophitai_algo_trading/
  framework/                    NEW
    __init__.py                 public exports
    models.py                   Insight, PortfolioTarget, AlgorithmContext (<150 lines)
    protocols.py                AlphaModel, PCM, Risk, Execution protocols (<100 lines)
    algorithm.py                Algorithm dataclass + validation (<100 lines)
    portfolio_construction/     directory — one model per file
      __init__.py               exports
      base.py                   shared helpers (cross-sec zscore, etc.)
      equal_weight.py           EqualWeightPCM
      insight_weighted.py       InsightWeightedPCM
      magnitude_ls.py           MagnitudeWeightedLongShortPCM
      multi_alpha_blend.py      MultiAlphaBlendPCM
    risk_management/
      __init__.py
      composite.py              CompositeRiskModel (runs list in sequence)
      drawdown.py               MaxDrawdownRiskModel (delever + cooldown)
      gross_cap.py              MaxGrossExposureRiskModel
      position_stops.py         wraps existing stops.py risk rules
      portfolio_limits.py       wraps existing limits.py risk rules
    execution/
      __init__.py
      simulated.py              SimulatedExecutionModel (writes to Portfolio)
      broker.py                 BrokerExecutionModel (calls Alpaca)

  alphas/                       NEW — built-in alphas; strategies live here post-migration
    __init__.py
    momentum.py
    breakout.py
    reversal.py
    low_vol.py
    trend_volume.py
    ... (more as added)

  # unchanged dirs:
  broker/ data/ engines/ indicators/ risk/ sizing/
  cost_model.py portfolio.py metrics.py enums.py

  # to be deleted at Phase 5 completion:
  strategy.py signals.py        (BaseStrategy + helpers — replaced by AlphaModel)
```

## What stays vs. what changes

**Stays untouched:**
- `Portfolio`, `Position`, `Trade` — the accounting layer
- `CostModel` — transaction costs
- `metrics.py` — post-run analytics
- `broker/alpaca.py` — broker wrapper
- `data/loader.py`, `data/stream/` — data sources
- `indicators/` — pure technical indicators
- `sizing/` — sizers stay as primitives **used by** PCMs

**Stays but rewrapped:**
- `risk/` — existing `RiskRule` instances stay; new `RiskManagementModel` wrappers compose them at the portfolio level. Risk rules work on `PortfolioTarget` objects instead of per-entry/per-exit hooks.

**Replaced:**
- `BaseStrategy` → deleted. Replaced by `AlphaModel` protocol + concrete alphas in `alphas/`.
- `strategy.py`, `signals.py` → deleted at end of Phase 5.

**Rewired:**
- `EventDrivenBacktest` — constructor takes an `Algorithm`, not strategy+sizer+risk_rules separately. Loop body calls `alpha.update() → pcm.create_targets() → risk.manage() → execution.execute()` per bar.
- `LiveRunner` — same constructor shape; wires `BrokerExecutionModel` instead of `SimulatedExecutionModel`.
- `VectorizedBacktest` — rewired as a **batch alpha evaluator** that materializes `Insight` streams into a position matrix and simulates portfolio in numpy. Lives alongside the event-driven engine for research sweeps; same `AlphaModel` input, different orchestration.

## Migration phases

Each phase is shippable independently. All phases must keep existing code runnable until Phase 5 flips the engines.

### Phase 0 — Dataclasses + ADR *(this doc)*
- Write `docs/algo_trading/framework.md` (this file)
- Write `framework/models.py` with `Insight`, `PortfolioTarget`, `AlgorithmContext`
- Write `framework/protocols.py` with 4 `Protocol` types + `Algorithm` dataclass
- Zero behavioral changes. No engine modifications yet.

### Phase 1 — AlphaModel + built-in alphas
- Implement the 5 alphas from `projects/qc_test/multi_alpha_daily/` as `AlphaModel` subclasses in `alphas/`
- Write unit tests — fixed-data inputs, assert Insight outputs
- `BaseStrategy` still exists; alphas are additive

### Phase 2 — PortfolioConstructionModel + built-ins
- Implement `EqualWeightPCM`, `InsightWeightedPCM`, `MagnitudeWeightedLongShortPCM`, `MultiAlphaBlendPCM`
- PCMs **use** existing sizers internally (composition over replacement)
- Unit tests — given insights + portfolio state, assert target outputs

### Phase 3 — RiskManagementModel + built-ins
- Implement `CompositeRiskModel`, `MaxDrawdownRiskModel`, `MaxGrossExposureRiskModel`
- `PositionStopsRiskModel` / `PortfolioLimitsRiskModel` wrap existing `RiskRule` classes so `stops.py`, `limits.py`, `windows.py`, `cooldowns.py` stay as-is
- Unit tests — given targets + portfolio state, assert modified targets

### Phase 4 — ExecutionModel + implementations
- Implement `SimulatedExecutionModel` — computes current holdings, diffs against targets, calls `portfolio.open()` / `portfolio.close()`
- Implement `BrokerExecutionModel` — same diff, calls `broker.buy()` / `broker.sell()` / `broker.close_position()`
- Unit tests — given targets + portfolio, assert the right `open`/`close` sequence fires

### Phase 5 — Rewire engines
- `EventDrivenBacktest` takes `Algorithm`, uses pipeline loop
- `LiveRunner` takes `Algorithm`, wires broker execution
- `VectorizedBacktest` takes `Algorithm`, materializes insights into position matrix
- **Update `projects/bt_test/` consumer** in the same PR (one downstream migration)
- Delete `strategy.py`, `signals.py`, remove `BaseStrategy` from `__init__.py`

**Total estimate:** 2-3 weeks of focused work. Phases 0-4 are independent; Phase 5 is the flip.

## Breaking changes (for `projects/bt_test/`)

After Phase 5:
- `from prophitai_algo_trading import BaseStrategy` → `from prophitai_algo_trading.framework import AlphaModel`
- `EventDrivenBacktest(strategy=..., sizer=..., risk_rules=...)` → `EventDrivenBacktest(algorithm=Algorithm(alphas=[...], portfolio_construction=..., risk_management=..., execution=...))`
- `VectorizedBacktest(strategy=..., cost_pct=...)` → same pattern
- `PassThroughStrategy` in `bt_test/strategy_base.py` → becomes `PassThroughAlpha`

These are mechanical edits; downstream migration takes ~1 hour.

## Non-goals (explicit YAGNI)

- **UniverseSelectionModel** — static universe lists remain. Revisit when dynamic universe filtering is needed.
- **Slice data type** — dict[str, DataFrame] per the existing engine shape. Move to `Slice` when corporate actions/dividends arrive.
- **Consolidators** — multi-timeframe indicators are a Phase 6 nice-to-have.
- **Brokerage model abstraction** — Alpaca-only. No IB/Tradier/Coinbase abstraction layer.
- **Per-security fee/slippage/fill models** — global `CostModel` is enough for daily US equities.
- **Options backtest engine** — out of scope for this refactor.
- **Fund pipeline integration** — downstream, not part of this work.

## Risks

1. **Vectorized engine semantic mismatch.** Event-driven is per-bar; vectorized is whole-matrix. Forcing both through `AlphaModel.update()` could slow vectorized down. **Mitigation:** add a `BatchAlphaModel` sibling protocol that emits a position matrix directly; ordinary `AlphaModel` works with an adapter that calls `update()` per bar.

2. **Cohort-aware sizing (BetaNeutralSizer.prepare_for_bar) loses its place.** Current design assumes sizer sees the whole entry cohort. **Mitigation:** the PCM owns the cohort entirely, so `MagnitudeWeightedLongShortPCM` (etc.) can call a cohort-aware sizer internally — the hook moves into PCM's pipeline, not lost.

3. **Risk rule semantic drift.** Current rules are entry-gate + exit-trigger; RiskManagementModel works on targets. Some rules (trailing stops) need per-symbol state tracked across bars. **Mitigation:** PositionStopsRiskModel holds the `RiskRule` instances, observes current positions from `ctx.portfolio`, and zeros the relevant target when a stop fires.

4. **`projects/bt_test/` breaks mid-migration.** **Mitigation:** Phase 5 does the consumer update in the same commit as the engine flip. Phases 0-4 don't touch the existing `EventDrivenBacktest` surface.

## Success criteria

- `projects/qc_test/multi_alpha_daily/` can be reimplemented in ~50 lines using `Algorithm(alphas=[...], ...)` post-Phase 5
- All existing sizers and risk rules still in use, wrapped by PCMs and RiskManagementModels
- Equity curves for identical-spec strategies pre/post migration match within numerical tolerance (< 0.1% end-equity delta)
- `projects/bt_test/` continues to run after the Phase 5 migration commit

## Open questions

- Should `Insight.period` be `timedelta` (Lean's choice) or `close_time: datetime` (easier math)? **Decision: `close_time`.** More explicit, no implicit "now + period" arithmetic at consumer sites.
- Should `PortfolioTarget.target_shares` be `float` or `int`? **Decision: `float`.** Fractional shares are supported by Alpaca; round at the execution boundary if needed.
- Should `AlgorithmContext` be mutable? **Decision: yes but frozen attributes for `timestamp`.** Portfolio state mutates naturally; timestamp is fixed per bar.
