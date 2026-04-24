# Algo Trading Framework — Overview

`prophitai_algo_trading` is a composable algorithm framework for research → backtest → deploy.  The same `Algorithm` object runs in backtest and live — only the engine driving the bar loop, and the execution sink embedded in the algorithm, differ.

## The four-stage pipeline

Every bar, for every `Algorithm`, the same four stages run in order:

```
AlphaModel.update(ctx)
        │  list[Insight]
        ▼
PortfolioConstructionModel.create_targets(ctx, insights)
        │  list[PortfolioTarget]
        ▼
RiskManagementModel.manage(ctx, targets)
        │  list[PortfolioTarget]  (possibly modified)
        ▼
ExecutionModel.execute(ctx, targets)
        │  side effects only (portfolio mutation or broker order)
        ▼
 (lifecycle diff: on_position_opened / on_position_closed fan out)
```

Each stage is a `Protocol` (see `core/protocols.py`) — duck-typed, no inheritance required.  Concrete implementations live in their own subpackages:

| Stage | Package | Built-ins |
|-------|---------|-----------|
| Alpha | `alphas/` | `MomentumAlpha`, `BreakoutAlpha`, `ShortTermReversalAlpha`, `TrendVolumeAlpha`, `LowVolAlpha`, `CointegrationPairAlpha` |
| Portfolio construction | `portfolio_construction/` | `EqualWeightPCM`, `InsightWeightedPCM`, `MagnitudeWeightedLongShortPCM`, `MultiAlphaBlendPCM` |
| Risk management | `risk/` | `StopLossExit`, `TrailingStopExit`, `TimeStop`, `ProfitTargetExit`, `ReentryCooldown`, `ConsecutiveLossCooldown`, `DailyLossLimit`, `PortfolioDrawdownLimit`, `TradingWindow`, `MaxDrawdownRiskModel`, `MaxGrossExposureRiskModel`, `CompositeRiskModel` |
| Execution | `execution/` | `ExecutionModel(sink=PortfolioSink())`, `ExecutionModel(sink=BrokerSink(broker))` |

## The `Algorithm` object

An `Algorithm` is a dataclass holding exactly one of each stage (plus a list of alphas).  Everything the engine needs to run lives on this one object:

```python
from prophitai_algo_trading import Algorithm
from prophitai_algo_trading.alphas import MomentumAlpha, BreakoutAlpha
from prophitai_algo_trading.portfolio_construction import (
    MagnitudeWeightedLongShortPCM, MultiAlphaBlendPCM,
)
from prophitai_algo_trading.risk import (
    CompositeRiskModel, MaxDrawdownRiskModel, MaxGrossExposureRiskModel,
)
from prophitai_algo_trading.execution import ExecutionModel, PortfolioSink

algo = Algorithm(
    alphas=[MomentumAlpha(), BreakoutAlpha()],
    portfolio_construction=MultiAlphaBlendPCM(
        weights={"momentum": 0.5, "breakout": 0.5},
        inner=MagnitudeWeightedLongShortPCM(gross_exposure=1.5),
    ),
    risk_management=CompositeRiskModel([
        MaxDrawdownRiskModel(max_drawdown_pct=0.15),
        MaxGrossExposureRiskModel(max_gross=1.5),
    ]),
    execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
)
```

Validation in `__post_init__`:

- At least one alpha required.
- Alpha names must be unique (multi-alpha PCMs partition insights by `source_alpha`).
- `algorithm.max_lookback` is derived automatically from `max(alpha.lookback)` — engines use this to set `ctx.warmup`.

## Backtest vs live

The only difference is the engine that drives bars and the sink inside `ExecutionModel`:

| Mode | Engine | Sink |
|------|--------|------|
| Backtest | `Backtest(algo, initial_capital=...).run(data)` | `PortfolioSink()` — mutates in-memory `Portfolio` |
| Live | `LiveRunner(algo, broker, tickers)` | `BrokerSink(broker)` — routes to Alpaca, mirrors fill |

The per-bar pipeline itself lives in `engines/runner.py::BarRunner.step` — both engines wrap this one method.  Backtest adds `force_flatten` at the end of the run so all open positions close through the normal execution + lifecycle path.

## Warmup

The engine sets `ctx.warmup = True` for the first `algorithm.max_lookback` bars.  During warmup:

- Alphas still tick (indicators need to populate).
- PCM still emits targets.
- Risk still manages.
- **`ExecutionModel` early-returns** — no orders fire.

This lets rolling indicators build state without dragging trading P&L through bars where signals aren't usable yet.

## Lifecycle events

After `ExecutionModel.execute`, `BarRunner` diffs pre- vs post-execute position state and fires:

- `on_position_opened(ctx, symbol)` — flat → long/short, or the open leg of a flip.
- `on_position_closed(ctx, symbol, pnl)` — long/short → flat, or the close leg of a flip.

These only fire if the risk model structurally satisfies `LifecycleAwareRiskModel` (i.e. defines both methods).  Stateful risk rules (`TrailingStopExit`, `TimeStop`, `ReentryCooldown`, `ConsecutiveLossCooldown`) use these hooks to track per-position state.

## File topology at a glance

```
src/prophitai_algo_trading/
  __init__.py                  # public re-exports (Algorithm, Backtest, LiveRunner, ...)
  core/                        # contracts — Algorithm, protocols, dataclasses
  alphas/                      # AlphaModel implementations + 3 base classes
  portfolio_construction/      # PCM implementations + helpers
  risk/                        # RiskManagementModel rules + composite
  execution/                   # ExecutionModel + OrderSink adapters
  accounting/                  # Portfolio, Position, Trade, CostModel
  engines/                     # Backtest, LiveRunner, BarRunner, lifecycle diff
  data/                        # CSV loader + ZMQ streaming (publish/subscribe)
  brokers/                     # Vendor integrations (Alpaca) + startup snapshots
  analytics/                   # BacktestResult + calculate_metrics
```

## Reading order for building a strategy

1. **`core.md`** — `Insight`, `PortfolioTarget`, `AlgorithmContext`, the protocols.
2. **`alphas.md`** — pick a base (`PerSymbolAlpha` / `CrossSectionalAlpha` / `PairAlpha`) and implement `compute_score`.
3. **`portfolio_construction.md`** — pick a PCM or compose `MultiAlphaBlendPCM` over one.
4. **`risk.md`** — stack rules in `CompositeRiskModel`.
5. **`execution.md`** — wire `ExecutionModel(sink=PortfolioSink())` for backtest.
6. **`engines.md`** — hand the algorithm to `Backtest.run(data)`.
7. **`cookbook.md`** — an end-to-end worked example that ties it all together.
