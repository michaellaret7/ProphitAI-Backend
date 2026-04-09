---
name: run_contract_tests
title: Running Strategy Contract Tests via Code Execution
description: Use after building a complete strategy (indicators + signals + config + strategy class) to validate it against the deterministic test harness. Covers writing the manifest, inheriting contract mixins, running pytest, and interpreting results.
created: 2026-04-09
updated: 2026-04-09
---

# Running Strategy Contract Tests

## When to Use
After all strategy components are built (indicator suite, signal model, config, strategy
class, and optionally risk controls), run the contract test harness to validate that
everything plugs into the framework correctly. This is the final verification step before
a strategy is considered implementation-complete.

## What the Tests Check
The test harness is **strategy-agnostic** — it validates structural conformance, not
trading logic:

- **Indicators**: Columns are added, NaN-free after warmup, OHLCV preserved, incremental
  path matches batch, idempotent
- **Signals**: Returns 4 bool Series (long_entry/exit, short_entry/exit), correct length,
  validates required columns, bounded scores
- **Config**: Defaults instantiate, frozen, positive period params
- **Strategy**: Is BaseComposableStrategy, min_bars_required > 0, full pipeline runs,
  builds valid EntryCandidate
- **Leakage** (critical): No indicator or signal values change when future bars are removed
- **Risk Controls**: Instantiate, return bools, lifecycle hooks don't crash

## Procedure

### Step 1: Write the Test File
Create a test file at `strategies/development/{{strategy_id}}/tests/test_contracts.py`:

```python
"""Contract tests for {{StrategyName}}."""

from prophitai_algo_trading.testing import (
    StrategyTestManifest,
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
)
from strategies.development.{{strategy_id}}.strategy import {{StrategyClass}}
from strategies.development.{{strategy_id}}.config import {{ConfigClass}}


class Test{{StrategyName}}Contracts(
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
):
    """All contract tests for {{StrategyName}}."""

    manifest = StrategyTestManifest(
        name="{{StrategyName}}",
        build_strategy=lambda: {{StrategyClass}}({{ConfigClass}}()),
        config_class={{ConfigClass}},
        min_warmup_bars={{max_warmup_from_indicators}},
    )
```

### Step 2: Add Risk Controls (if applicable)
If the strategy has custom risk controls, add the `RiskControlContract` mixin
and `build_risk_controls` to the manifest:

```python
from prophitai_algo_trading.testing import RiskControlContract
from strategies.development.{{strategy_id}}.risk_controls import MyCooldown, MyTrailingStop

class Test{{StrategyName}}Contracts(
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
    RiskControlContract,  # Add this mixin
):
    manifest = StrategyTestManifest(
        name="{{StrategyName}}",
        build_strategy=lambda: {{StrategyClass}}({{ConfigClass}}()),
        config_class={{ConfigClass}},
        min_warmup_bars={{max_warmup_from_indicators}},
        build_risk_controls=lambda: [
            MyCooldown(window=5),
            MyTrailingStop(atr_multiple=2.0),
        ],
    )
```

### Step 3: Run the Tests
Execute via sandbox bash:

```bash
cd /home/user/strategies && python -m pytest \
    strategies/development/{{strategy_id}}/tests/test_contracts.py \
    -v --tb=short 2>&1
```

### Step 4: Interpret Results

**All tests pass:**
```
======================== 41 passed in 0.93s =========================
```
Strategy is structurally sound. All interfaces conform to the framework.

**Leakage test failure** (CRITICAL — must fix):
```
FAILED test_no_signal_leakage[uptrend-30]
    Future leakage in 'long_entry' at bar 60: full=True, truncated=False
```
This means the signal at bar 60 changes depending on whether future bars exist.
Common causes:
- Using `df.iloc[-1]` instead of a proper rolling window
- Using `shift(-n)` (forward shift instead of backward)
- Normalizing with `rank()` or `pct_change()` over the entire series
- Using `df["col"].mean()` (global mean) instead of rolling mean

**NaN after warmup failure:**
```
FAILED test_no_nan_after_warmup
    NaN after warmup in: {'custom_indicator': 15}
```
The `min_warmup_bars` in the manifest is too low, or the indicator has a bug
producing NaN for some bars. Fix: increase warmup or fix the indicator.

**update_last_row mismatch:**
```
FAILED test_update_last_row_matches_calculate
    Series are different: sma_fast ...
```
The incremental update path diverges from batch calculation. This means live
trading will produce different indicator values than backtesting. Fix the
indicator's `update_last_row()` implementation.

**Missing columns raises failure:**
```
FAILED test_missing_columns_raises
    DID NOT RAISE <class 'ValueError'>
```
The signal model's `required_columns` tuple is empty. Add the columns that
the signal model depends on to `required_columns`.

## Key Rules

1. **`build_strategy` must be a lambda/callable**, not an instance. Each test calls
   it fresh to avoid `IndicatorPipeline._instances` cache contamination.

2. **`min_warmup_bars` must match or exceed the slowest indicator's lookback period.**
   For example, if you use SMA(50) and RSI(14), set `min_warmup_bars=50`.

3. **Every test class must inherit from at least `IndicatorSuiteContract` and
   `LeakageContract`** — these are the minimum viable contracts.

4. **Do not add strategy-specific assertions** to the contract test class. The
   contracts are strategy-agnostic by design. Strategy-specific logic tests
   belong in a separate test file.

5. **If a test fails, fix the strategy code, not the test.** The contracts test
   universal invariants that every strategy must satisfy.

## Available Fixtures for Custom Tests

If you need to write additional tests beyond the contracts, these deterministic
fixtures are available:

```python
from prophitai_algo_trading.testing import (
    uptrend,           # Monotonic exponential rise
    downtrend,         # Monotonic exponential decline
    mean_reverting,    # Sine wave oscillation
    flat,              # Constant price
    volatile_breakout, # Flat → steep breakout
    gap_up,            # Trend with 5% gap up
    gap_down,          # Trend with 5% gap down
    make_ohlcv,        # Build custom fixture from close prices
)
```

## Revision Log
- 2026-04-09: Created after building the strategy test harness in prophitai_algo_trading.
