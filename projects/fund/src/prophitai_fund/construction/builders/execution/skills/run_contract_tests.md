---
name: run_contract_tests
title: Running Execution Layer Contract Tests
description: Use after building risk controls, position sizing, and runner scripts to validate that risk controls conform to the RiskControl interface. Assumes indicator and signal contracts already pass. Scoped to risk control contracts only.
created: 2026-04-09
updated: 2026-04-09
---

# Running Execution Layer Contract Tests

## When to Use
After building risk controls, position sizing logic, and wiring/runner scripts —
and AFTER both the Indicator Builder's and Signal+Strategy Builder's tests have
passed. This validates that the execution layer's risk controls conform to the
framework interface.

## What These Tests Check
Only contracts relevant to the execution layer:

- **RiskControlContract** (4 tests): Risk controls instantiate as `RiskControl`
  instances, `should_block_entry()` returns bool, `should_force_exit()` returns
  bool, lifecycle hooks (`on_entry`, `on_exit`, `on_bar`) run without raising

## What These Tests Do NOT Check
The following are **not your responsibility**:

- Indicator columns, NaN, OHLCV preservation, incremental parity (Indicator Builder)
- Indicator leakage (Indicator Builder)
- Signal model outputs, required columns, bounded scores (Signal+Strategy Builder)
- Config structure (Signal+Strategy Builder)
- Strategy integration / pipeline (Signal+Strategy Builder)
- Signal leakage (Signal+Strategy Builder)

## Procedure

### Step 1: Run the Tests via sandbox_bash
Execute the test inline — no test file needed:

```bash
sandbox_bash(sandbox_id, """
cd /home/user/strategies && python -c "
import sys
from prophitai_algo_trading.testing import (
    StrategyTestManifest,
    RiskControlContract,
)
from strategies.development.{{strategy_id}}.strategy import {{StrategyClass}}
from strategies.development.{{strategy_id}}.config import {{ConfigClass}}
from strategies.development.{{strategy_id}}.risk_controls import (
    {{RiskControlClass1}},
    {{RiskControlClass2}},
)

class TestExecution(RiskControlContract):
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

Expected passing count: **4 tests**.

### Step 2: Interpret Results

**All tests pass:**
```
======================== 4 passed in 0.5s =========================
```
Risk controls conform to the framework interface. Proceed to full suite validation.

**Risk control not a RiskControl instance:**
```
FAILED test_risk_controls_instantiate
    MyCooldown is not a RiskControl
```
The risk control class does not inherit from `prophitai_algo_trading.risk.base.RiskControl`.
Ensure the class inherits from `RiskControl` and implements all abstract methods.

**should_block_entry does not return bool:**
```
FAILED test_should_block_entry_returns_bool
    MyCooldown.should_block_entry returned NoneType, not bool
```
The method is not returning a value, or returns None in some code path. Ensure
every code path returns `True` or `False`. Common causes:
- Missing `return` statement in a conditional branch
- Returning the result of a method that returns None

**should_force_exit does not return bool:**
```
FAILED test_should_force_exit_returns_bool
    MyTrailingStop.should_force_exit returned NoneType, not bool
```
Same issue as above — ensure every path returns a bool.

**Lifecycle hooks crash:**
```
FAILED test_lifecycle_hooks_callable
    TypeError: on_entry() missing 1 required positional argument: 'direction'
```
The lifecycle hook signature does not match the base class. Check that your
methods accept the correct arguments:
- `on_entry(self, ticker: str, price: float, timestamp: datetime, direction: Direction)`
- `on_exit(self, ticker: str, price: float, timestamp: datetime, direction: Direction)`
- `on_bar(self, ticker: str, price: float, timestamp: datetime)`

Common causes:
- Forgetting the `direction` parameter on `on_entry`/`on_exit`
- Incorrect parameter order
- Not calling `super().on_entry(...)` when the base class has default behavior

## Key Rules

1. **`build_risk_controls` must be a lambda/callable** returning a list of
   `RiskControl` instances. Each test calls it fresh.

2. **Only inherit `RiskControlContract`** — do not inherit indicator, signal,
   config, strategy, or leakage contracts. Those are upstream builders' concern.

3. **If a test fails, fix the risk control code, not the test.** The contracts
   test universal invariants that every risk control must satisfy.

4. **If the strategy has no custom risk controls**, skip this test entirely.
   Only run it when `build_risk_controls` is declared in the manifest.

5. **Risk controls must be stateless across test runs.** If a risk control
   maintains internal state (e.g., cooldown timestamps), ensure the constructor
   initializes it cleanly.

## Revision Log
- 2026-04-09: Created as scoped execution layer testing skill with inline execution.
