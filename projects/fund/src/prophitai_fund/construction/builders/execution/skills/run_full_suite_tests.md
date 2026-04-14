---
name: run_full_suite_tests
title: Running Full Suite Contract Tests
description: Use as the final integration gate after all 3 builders (Indicator, Signal+Strategy, Execution) have passed their scoped tests. Runs ALL 6 contract mixins in a single test class to catch seam issues between layers.
created: 2026-04-09
updated: 2026-04-09
---

# Running Full Suite Contract Tests

## When to Use
After ALL three scoped test suites pass individually:
1. Indicator contracts — PASSED
2. Signal+Strategy contracts — PASSED
3. Execution contracts — PASSED

This is the **final integration gate** before a strategy is considered
implementation-complete. It catches issues at the seams between layers that
scoped tests miss.

## What These Tests Check
All 6 contract mixins together:

- **IndicatorSuiteContract** (7 tests): Columns, NaN, OHLCV, incremental parity,
  idempotency, all fixtures
- **SignalModelContract** (5 tests): 4 bool Series, length, required columns, scores
- **ConfigContract** (3 tests): Defaults, frozen, positive periods
- **StrategyContract** (5 tests): Composable, min_bars, pipeline, scores, candidates
- **LeakageContract** (18 parametrized): Both indicator AND signal leakage
- **RiskControlContract** (4 tests): Instantiation, bools, lifecycle hooks

## What This Catches That Scoped Tests Miss
- Column contract mismatches (indicator outputs vs. signal required_columns)
- Config values that work in isolation but break downstream (e.g., warmup mismatch)
- Interaction effects between indicator enrichment and signal generation
- Risk controls that depend on strategy state not available in isolation

## Procedure

### Step 1: Run the Full Suite via sandbox_bash
Execute the test inline — no test file needed, no `-k` filters, run everything:

```bash
sandbox_bash(sandbox_id, """
cd /home/user/strategies && python -c "
import sys
from prophitai_algo_trading.testing import (
    StrategyTestManifest,
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
    RiskControlContract,
)
from strategies.development.{{strategy_id}}.strategy import {{StrategyClass}}
from strategies.development.{{strategy_id}}.config import {{ConfigClass}}
from strategies.development.{{strategy_id}}.risk_controls import (
    {{RiskControlClass1}},
    {{RiskControlClass2}},
)

class TestFullSuite(
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
    RiskControlContract,
):
    manifest = StrategyTestManifest(
        name='{{StrategyName}}',
        build_strategy=lambda: {{StrategyClass}}({{ConfigClass}}()),
        config_class={{ConfigClass}},
        min_warmup_bars={{max_warmup_from_indicators}},
        build_risk_controls=lambda: [
            {{RiskControlClass1}}({{params}}),
            {{RiskControlClass2}}({{params}}),
        ],
    )

sys.exit(
    __import__('pytest').main([
        __file__,
        '-v', '--tb=short',
    ])
)
" 2>&1
""")
```

Expected passing count: **~42 tests** (7 indicator + 5 signal + 3 config + 5
strategy + 18 leakage + 4 risk control).

### Step 2: Interpret Results

**All tests pass:**
```
======================== 42 passed in 1.5s =========================
```
Strategy is implementation-complete. All layers conform to framework contracts
and integrate correctly.

**A test fails that passed in scoped tests:**
This indicates a seam issue — something that works in isolation but breaks when
all layers interact. Common examples:

- **Signal requires a column the indicator suite doesn't produce:**
  The signal model's `required_columns` includes a column name that doesn't match
  the indicator's actual output column name (typo, naming drift between builders).

- **Leakage appears only with full pipeline:**
  An indicator is leak-free in isolation, but when the signal model's `enrich()`
  adds derived columns using global operations, those derived columns leak.

- **Config warmup mismatch:**
  The `min_warmup_bars` works for indicators but is too low for the combined
  indicator + signal warmup (e.g., signal uses a rolling window on top of indicators).

**A test fails that also failed in scoped tests:**
This should not happen if scoped suites were run first. Re-run the scoped test
for the responsible builder and fix there first.

## Key Rules

1. **Run this ONLY after all 3 scoped suites pass.** Do not use the full suite
   as a substitute for scoped testing — it's harder to diagnose failures when
   all contracts run together.

2. **If a test fails here but passed in scoped tests, the issue is at a seam.**
   Focus on the interface between the two layers the failing contract touches.

3. **`build_strategy` must be a lambda/callable** — same rule as scoped tests.

4. **If the strategy has no custom risk controls**, omit `RiskControlContract`
   from the inheritance list and `build_risk_controls` from the manifest.

5. **This is the final gate.** A strategy that passes the full suite is ready
   for backtesting and live deployment.

## Revision Log
- 2026-04-09: Created as final integration gate skill with inline execution.
