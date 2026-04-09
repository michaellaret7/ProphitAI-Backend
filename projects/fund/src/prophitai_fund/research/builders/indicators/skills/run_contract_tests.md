---
name: run_contract_tests
title: Running Indicator Contract Tests
description: Use after building an indicator suite (custom indicators + derived features) to validate structural conformance and detect indicator-level future leakage. Scoped to indicator-only contracts — does NOT cover signals, config, strategy, or risk controls.
created: 2026-04-09
updated: 2026-04-09
---

# Running Indicator Contract Tests

## When to Use
After building the indicator suite, custom indicators, and derived features — but
BEFORE the Signal+Strategy Builder runs. This validates that the indicator layer
is structurally sound and leak-free in isolation.

## What These Tests Check
Only contracts relevant to the indicator layer:

- **IndicatorSuiteContract** (7 tests): Columns are added, NaN-free after warmup,
  OHLCV preserved, incremental path matches batch, idempotent, runs on all fixtures
- **LeakageContract — indicator leakage only** (9 parametrized): Indicator values
  at bar N are identical whether computed on the full series or a truncated series
  ending at bar N

## What These Tests Do NOT Check
The following are **not your responsibility** — they belong to downstream builders:

- Signal model outputs (Signal+Strategy Builder)
- Config dataclass structure (Signal+Strategy Builder)
- Strategy integration / pipeline (Signal+Strategy Builder)
- Signal leakage (Signal+Strategy Builder)
- Risk controls (Execution Builder)

## Procedure

### Step 1: Run the Tests via sandbox_bash
Execute the test inline — no test file needed. Use `sandbox_bash` with `-k` to
exclude signal leakage tests:

```bash
sandbox_bash(sandbox_id, """
cd /home/user/strategies && python -m pytest --co -q 2>&1 | head -5
python -c "
import sys
from prophitai_algo_trading.testing import (
    StrategyTestManifest,
    IndicatorSuiteContract,
    LeakageContract,
)
from strategies.development.{{strategy_id}}.strategy import {{StrategyClass}}
from strategies.development.{{strategy_id}}.config import {{ConfigClass}}

class TestIndicators(IndicatorSuiteContract, LeakageContract):
    manifest = StrategyTestManifest(
        name='{{StrategyName}}',
        build_strategy=lambda: {{StrategyClass}}({{ConfigClass}}()),
        config_class={{ConfigClass}},
        min_warmup_bars={{max_warmup_from_indicators}},
    )

sys.exit(
    __import__('pytest').main([
        __file__,
        '-k', 'not test_no_signal_leakage',
        '-v', '--tb=short',
    ])
)
" 2>&1
""")
```

Expected passing count: **~19 tests** (7 indicator suite + 3 fixture variants + 9
indicator leakage parametrizations).

### Step 2: Interpret Results

**All tests pass:**
```
======================== 19 passed in 0.8s =========================
```
Indicator layer is structurally sound. Hand off to Signal+Strategy Builder.

**NaN after warmup failure:**
```
FAILED test_no_nan_after_warmup
    NaN after warmup in: {'custom_rsi': 15}
```
The `min_warmup_bars` in the manifest is too low, or the indicator produces NaN
for some bars. Fix: increase warmup to match the slowest indicator's lookback, or
fix the indicator calculation.

**update_last_row mismatch:**
```
FAILED test_update_last_row_matches_calculate
    Series are different: sma_fast ...
```
The incremental update path diverges from batch calculation. This means live
trading will produce different values than backtesting. Fix the indicator's
`update_last_row()` implementation. Common causes:
- Using state that is not reset between calls
- Off-by-one in the rolling window slice
- Forgetting to update a derived column that depends on a base indicator

**Indicator leakage failure** (CRITICAL):
```
FAILED test_no_indicator_leakage[uptrend-30]
    indicator leakage at bar 80: Series are different: sma_custom ...
```
An indicator value at bar 80 changes when future bars are removed. Common causes:
- Using `df["col"].mean()` (global mean) instead of `.rolling(n).mean()`
- Using `rank()` or `pct_change()` over the entire series
- Normalizing with min/max of the full series
- Any operation that reads the full column instead of a backward-looking window

**Fixture failure (runs_on_all_fixtures):**
```
FAILED test_runs_on_all_fixtures[flat]
```
The indicator crashes on flat/constant price data. Common cause: division by zero
in volatility or range-based indicators when high == low == close.

## Key Rules

1. **`build_strategy` must be a lambda/callable**, not an instance. Each test calls
   it fresh to avoid `IndicatorPipeline._instances` cache contamination.

2. **`min_warmup_bars` must match or exceed the slowest indicator's lookback period.**
   For example, if you use SMA(50) and RSI(14), set `min_warmup_bars=50`.

3. **If a test fails, fix the indicator code, not the test.** The contracts test
   universal invariants that every indicator suite must satisfy.

4. **Only run indicator-scoped tests.** Do not inherit SignalModelContract,
   ConfigContract, StrategyContract, or RiskControlContract — those are for
   downstream builders.

## Revision Log
- 2026-04-09: Scoped down from full-suite skill to indicator-only contracts.
  Switched from file creation to inline execution via sandbox_bash.
