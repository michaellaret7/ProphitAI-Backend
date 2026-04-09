---
name: run_contract_tests
title: Running Signal & Strategy Contract Tests
description: Use after building the signal model, strategy class, and config dataclass to validate structural conformance and detect signal-level future leakage. Assumes indicator contracts already pass. Does NOT cover risk controls.
created: 2026-04-09
updated: 2026-04-09
---

# Running Signal & Strategy Contract Tests

## When to Use
After building the signal model, strategy class, and config dataclass — and AFTER
the Indicator Builder's tests have passed. This validates that the signal and
strategy layers are structurally sound and leak-free.

## What These Tests Check
Only contracts relevant to the signal and strategy layers:

- **SignalModelContract** (5 tests): Returns 4 bool Series (long_entry/exit,
  short_entry/exit), correct length, validates required columns, bounded scores
- **ConfigContract** (3 tests): Defaults instantiate, frozen dataclass, positive
  period params
- **StrategyContract** (5 tests): Is BaseComposableStrategy, min_bars_required > 0,
  full pipeline runs, score_entries returns Series, builds valid EntryCandidate
- **LeakageContract — signal leakage only** (9 parametrized): Signal values at
  bar N are identical whether computed on the full series or a truncated series

## What These Tests Do NOT Check
The following are **not your responsibility**:

- Indicator column presence, NaN, OHLCV preservation, incremental parity (Indicator Builder — should already pass)
- Indicator leakage (Indicator Builder — should already pass)
- Risk controls: instantiation, should_block_entry, should_force_exit, lifecycle hooks (Execution Builder)

## Procedure

### Step 1: Run the Tests via sandbox_bash
Execute the test inline — no test file needed. Use `-k` to exclude indicator
leakage tests:

```bash
sandbox_bash(sandbox_id, """
cd /home/user/strategies && python -c "
import sys
from prophitai_algo_trading.testing import (
    StrategyTestManifest,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
)
from strategies.development.{{strategy_id}}.strategy import {{StrategyClass}}
from strategies.development.{{strategy_id}}.config import {{ConfigClass}}

class TestSignalStrategy(SignalModelContract, ConfigContract, StrategyContract, LeakageContract):
    manifest = StrategyTestManifest(
        name='{{StrategyName}}',
        build_strategy=lambda: {{StrategyClass}}({{ConfigClass}}()),
        config_class={{ConfigClass}},
        min_warmup_bars={{max_warmup_from_indicators}},
    )

sys.exit(
    __import__('pytest').main([
        __file__,
        '-k', 'not test_no_indicator_leakage',
        '-v', '--tb=short',
    ])
)
" 2>&1
""")
```

Expected passing count: **~22 tests** (5 signal + 3 config + 5 strategy + 9 signal
leakage parametrizations).

### Step 2: Interpret Results

**All tests pass:**
```
======================== 22 passed in 1.1s =========================
```
Signal and strategy layers are structurally sound. Hand off to Execution Builder.

**Signal returns wrong keys or types:**
```
FAILED test_generate_returns_four_keys
    assert {'long_entry', 'short_entry'} == {'long_entry', 'long_exit', 'short_entry', 'short_exit'}
```
The signal model's `generate()` is not returning all 4 required keys. Ensure
`long_entry()`, `long_exit()`, `short_entry()`, and `short_exit()` all return
`pd.Series` with dtype `bool`.

**Signals are not bool:**
```
FAILED test_signals_are_bool_series
    long_entry dtype is float64, not bool
```
Common causes:
- Returning a comparison result that includes NaN (NaN poisons bool dtype)
- Forgetting `.fillna(False)` after a comparison involving shifted columns
- Using numeric thresholds without converting to bool

**Missing columns validation failure:**
```
FAILED test_missing_columns_raises
    DID NOT RAISE <class 'ValueError'>
```
The signal model's `required_columns` tuple is empty or missing. Add every indicator
column the signal model reads to `required_columns`. This protects against running
the signal model on un-enriched data.

**Config not frozen:**
```
FAILED test_frozen
    MyConfig is not frozen
```
Add `frozen=True` to the `@dataclass` decorator.

**min_bars_required is 0:**
```
FAILED test_min_bars_required_positive
    min_bars_required should be > 0 for any real strategy
```
The strategy's `min_bars_required` property returns 0 or is not implemented.
It should return the slowest indicator's lookback period.

**Signal leakage failure** (CRITICAL):
```
FAILED test_no_signal_leakage[uptrend-30]
    Future leakage in 'long_entry' at bar 80: full=True, truncated=False
```
A signal at bar 80 changes depending on whether future bars exist. Common causes:
- Using `df.iloc[-1]` instead of a proper rolling window
- Using `shift(-n)` (forward shift instead of backward)
- Signal logic that depends on global statistics (full-series rank, mean, etc.)
- Threshold computed from the full series rather than a rolling window

**Score entries failure:**
```
FAILED test_score_entries_bounded
    score_entries contains NaN
```
The `score_entries()` method produces NaN. Common cause: dividing by an indicator
that is zero or NaN during warmup. Ensure scores are computed only on post-warmup
rows or use `.fillna(0)`.

**EntryCandidate failure:**
```
FAILED test_build_entry_candidate
    assert candidate.price > 0
```
The `build_entry_candidate()` method is not extracting price correctly from the
enriched row. Ensure it reads from `row["close"]` or the appropriate price column.

## Key Rules

1. **`build_strategy` must be a lambda/callable**, not an instance.

2. **`min_warmup_bars` must match the value set by the Indicator Builder.**

3. **If indicator leakage tests appear in output, ignore them** — use `-k` to
   exclude. Indicator leakage is the Indicator Builder's responsibility.

4. **If a test fails, fix the signal/strategy/config code, not the test.**

5. **Do not inherit IndicatorSuiteContract or RiskControlContract** — those belong
   to other builders.

## Revision Log
- 2026-04-09: Created as scoped signal+strategy testing skill with inline execution.
