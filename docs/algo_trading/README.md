# Algo Trading Wiki

Full reference documentation for the `prophitai_algo_trading` package.  These pages are written for agents building strategies — every page is self-contained, every decision is spelled out, every built-in is listed with defaults.

## Reading order

If you're an agent building a new strategy for the first time, read in this order:

1. **[overview.md](overview.md)** — pipeline, `Algorithm` composition, backtest vs live.
2. **[core.md](core.md)** — `Insight`, `PortfolioTarget`, `AlgorithmContext`, protocols.
3. **[alphas.md](alphas.md)** — `PerSymbolAlpha`, `CrossSectionalAlpha`, `PairAlpha`, how to author one.
4. **[portfolio_construction.md](portfolio_construction.md)** — PCM protocol, built-ins, helpers, composition.
5. **[risk.md](risk.md)** — rules, composite, lifecycle hooks, target-list transforms.
6. **[execution.md](execution.md)** — decision matrix, sinks, warmup, material-change filter.
7. **[accounting.md](accounting.md)** — `Portfolio`, `Position`, `Trade`, `CostModel`.
8. **[engines.md](engines.md)** — `Backtest`, `LiveRunner`, `BarRunner`, warmup, lifecycle.
9. **[data.md](data.md)** — DataFrame shape, CSV loader, DB loader, live streaming.
10. **[brokers.md](brokers.md)** — `Alpaca` facade, startup snapshots, adding a new vendor.
11. **[analytics.md](analytics.md)** — `BacktestResult`, `calculate_metrics`, active-window trim.
12. **[cookbook.md](cookbook.md)** — end-to-end worked example, copy-paste starting point.

## Quick links

### By task

| Task | Read |
|------|------|
| Write a new signal | [alphas.md](alphas.md) |
| Combine multiple alphas | [portfolio_construction.md](portfolio_construction.md) `#MultiAlphaBlender` |
| Add a stop-loss / trailing stop | [risk.md](risk.md) `#Exits` |
| Cap gross exposure | [risk.md](risk.md) `#MaxGrossExposureRiskModel` |
| Swap backtest → live | [execution.md](execution.md) `#The-sink-pattern` |
| Read equity / positions from an alpha | [accounting.md](accounting.md) `#Reading-state` |
| Load historical data | [data.md](data.md) |
| Understand a metric value | [analytics.md](analytics.md) |
| Start from a working template | [cookbook.md](cookbook.md) |

### By pipeline stage

```
AlphaModel.update(ctx)                          →  alphas.md
PortfolioConstructor.create_targets(...)  →  portfolio_construction.md
RiskManagementModel.manage(...)                 →  risk.md
ExecutionModel.execute(...)                     →  execution.md
```

## Package layout

```
packages/algo_trading/
  src/prophitai_algo_trading/
    __init__.py              # public re-exports
    core/                    # contracts (Algorithm, protocols, dataclasses)
    alphas/                  # AlphaModel implementations + 3 base classes
    portfolio_construction/  # PCM implementations + helpers
    risk/                    # RiskManagementModel rules + composite
    execution/               # ExecutionModel + OrderSink adapters
    accounting/              # Portfolio, Position, Trade, CostModel
    engines/                 # Backtest, LiveRunner, BarRunner, lifecycle
    data/                    # CSV loader + ZMQ streaming
    brokers/                 # Vendor integrations (Alpaca)
    analytics/               # BacktestResult + calculate_metrics
  tests/
    test_strategy/           # Reference 8-alpha strategy — copy this to start
```

## Reference implementations

The `packages/algo_trading/tests/test_strategy/` folder is a complete, runnable strategy covering all patterns — multi-alpha blending, cross-sectional alphas, pair trading, composite risk, cost-aware backtesting.  Copy from it when building a new strategy.

| File | What it shows |
|------|---------------|
| `universe.py` | 150-ticker universe, sector pairs, DB-backed loader |
| `alphas/*.py` | 7 custom alphas across all three base classes |
| `algorithm.py` | Multi-alpha + blended PCM + composite risk + backtest execution |
| `run.py` | Entry point — data → algorithm → backtest → grade |
| `grading.py` | Pipeline-break smoke test (not a P&L validator) |

## Public API

Everything that matters is re-exported from `prophitai_algo_trading`:

```python
from prophitai_algo_trading import (
    # Framework core
    Algorithm, AlgorithmContext, Insight, PortfolioTarget, MarketDataView,
    AlphaModel, PortfolioConstructor, RiskManagementModel, ExecutionModel,
    # Engines
    Backtest, BarRunner, LiveRunner,
    # Portfolio / accounting
    Portfolio, Position, Trade, CostModel,
    # Enums + metrics
    Direction, BacktestResult, calculate_metrics,
    # Data + broker
    load_csv_data, Alpaca,
)
```

Subpackages carry the rest:

- `prophitai_algo_trading.alphas` — built-in alphas + bases.
- `prophitai_algo_trading.portfolio_construction` — PCMs.
- `prophitai_algo_trading.risk` — rules + composite.
- `prophitai_algo_trading.execution` — `ExecutionModel` + sinks.

## Conventions that matter

1. **Alpha `name` is unique.**  `Algorithm.__post_init__` enforces it; multi-alpha PCMs key on it.
2. **`Insight.direction` is `int`** (`+1 / -1 / 0`), NOT the `Direction` enum.
3. **`PortfolioTarget.target_shares` is signed.**  `0.0` means flatten.  Symbols absent from the list are left alone.
4. **Only the sink mutates `portfolio`.**  Alphas / PCM / risk read, never write.
5. **Do not override `update()` on an alpha base.**  Enforced at class-definition time.
6. **`weight_to_shares(ctx, symbol, weight, direction)`** is the canonical conversion.  Don't re-roll the math.
7. **Fill prices are the current bar's close.**  No `next_open` option yet.
8. **Warmup suppresses execution, not alphas.**  Indicators still tick.
9. **Order of rules in a composite matters.**  Portfolio-wide → position-level → gross cap.
10. **DataFrame columns are lowercase**: `open, high, low, close, volume`.
