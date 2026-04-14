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

## CRITICAL: prophitai_algo_trading.testing Does NOT Exist
The `prophitai_algo_trading.testing` module referenced in the original skill content
**does not exist in the installed package** (confirmed AQM52 build 2026-04-09).
`pytest` is also **not installed** in the venv. You must write manual contract tests.

## What to Test
Write a manual Python script that validates:

1. **ConfigContract**: defaults instantiate, frozen (mutation raises), correct fields
2. **StrategyContract**: isinstance BaseComposableStrategy, min_bars_required > 0 and correct, calculate_indicators runs, get_sizing_hints returns dict
3. **SignalModelContract**: validate() passes on complete df, validate() raises on missing col, enrich() adds expected columns, generate() returns 4 bool Series of correct length, score_entries() returns float Series with no NaN
4. **LeakageContract**: signal values at bar N are identical whether computed on full or truncated series

## Procedure

### Step 1: Build synthetic test data
Create a DataFrame with `n=300` rows on a business-day DatetimeIndex with:
- All raw OHLCV columns
- All indicator output columns (manually computed or with realistic mock values)
- All derived feature columns (h52_ratio, h52_quintile_entry, etc.)

### Step 2: Run all contract checks in a single inline script

```python
cd /home/user/strategies && /home/user/strategies/.venv/bin/python -c "
import pandas as pd
import numpy as np
from strategies.development.{strategy_id}.config import {ConfigClass}
from strategies.development.{strategy_id}.strategy import {StrategyClass}
from strategies.development.{strategy_id}.signals.model import {SignalModelClass}
from prophitai_algo_trading import BaseComposableStrategy
from prophitai_algo_trading.signals import BaseSignalModel
import dataclasses

errors = []

# ConfigContract
cfg = {ConfigClass}()
try:
    cfg.some_field = 99  # Should raise FrozenInstanceError
    errors.append('Config is not frozen')
except Exception:
    pass  # Expected

# StrategyContract
strat = {StrategyClass}({ConfigClass}())
assert isinstance(strat, BaseComposableStrategy)
assert strat.min_bars_required == {expected_min_bars}

# Build synthetic df with all required columns...
# (populate as needed based on strategy's required_columns)

model = {SignalModelClass}()

# validate passes on complete df
model.validate(df)

# validate raises on missing column
try:
    model.validate(df.drop(columns=[model.required_columns[0]]))
    errors.append('validate did not raise on missing column')
except (ValueError, KeyError):
    pass

# generate returns 4 bool Series
signals = model.generate(df)
assert set(signals.keys()) == {'long_entry', 'long_exit', 'short_entry', 'short_exit'}
for k, v in signals.items():
    assert isinstance(v, pd.Series) and v.dtype == bool and len(v) == len(df)

# score_entries: no NaN
scores = model.score_entries(df)
assert not scores.isna().any()

# Leakage check
for bar in [260, 270, 280]:
    sig_full = model.generate(df)
    sig_trunc = model.generate(df.iloc[:bar+1].copy())
    for k in ['long_entry', 'long_exit']:
        if sig_full[k].iloc[bar] != sig_trunc[k].iloc[bar]:
            errors.append(f'LEAKAGE: {k} at bar {bar}')

print('Errors:', errors if errors else 'NONE — ALL PASS')
"
```

### Step 3: Interpret Results
- Zero errors → hand off to Execution Builder
- Any leakage error → check enrich() for global statistics or forward-looking indexing
- NaN in score_entries → add `.fillna(0.0)` on the returned Series
- validate not raising → ensure required_columns is non-empty tuple

## Key Rules

1. **pytest is NOT installed** — use inline Python assertions only
2. **prophitai_algo_trading.testing does NOT exist** — write manual checks
3. Use `/home/user/strategies/.venv/bin/python` explicitly (not `python -m`)
4. Build synthetic data that covers post-warmup bars (bar index > min_bars_required)
5. For leakage: test signal values at bars well past warmup (260, 270, 280 for 252-bar warmup)

## Pitfalls
- `python -m pytest` will silently return exit code 0 with no output if pytest is not installed
- Using `source .venv/bin/activate` in sandbox_bash does not persist across commands
- Always use the full venv python path: `/home/user/strategies/.venv/bin/python`

## Confirmed Patterns
- AQM52 (2026-04): Manual inline test script validated all 4 contract areas successfully

## Revision Log
- 2026-04-09: Created after building AQM52 signal+strategy layer
- 2026-04-09: MAJOR UPDATE — prophitai_algo_trading.testing does not exist, pytest not installed; replaced with manual inline test approach

