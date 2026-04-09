# Strategy Test Harness

Deterministic testing infrastructure for composable trading strategies. Ships with `prophitai_algo_trading` so any strategy repo gets contract tests for free.

## Architecture

```
Manifest (what to test)  +  Contract Mixins (how to test)  =  Full test suite
```

A strategy declares a single `StrategyTestManifest`. The consumer inherits from contract mixin classes. Pytest discovers all `test_*` methods from the mixins — zero bespoke test code.

## Quick Start

```python
# my_strategy/tests/test_contracts.py
from prophitai_algo_trading.testing import (
    StrategyTestManifest,
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
    RiskControlContract,
)
from my_strategy import MyStrategy, MyConfig
from my_strategy.risk import MyCooldown


class TestMyStrategy(
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
    RiskControlContract,
):
    manifest = StrategyTestManifest(
        name="MyStrategy",
        build_strategy=lambda: MyStrategy(MyConfig()),
        config_class=MyConfig,
        min_warmup_bars=50,
        build_risk_controls=lambda: [MyCooldown(window=5)],
    )
```

Run: `pytest my_strategy/tests/test_contracts.py -v`

## Manifest Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | required | Human-readable strategy name (pytest ID) |
| `build_strategy` | `Callable` | required | Zero-arg factory returning a `BaseComposableStrategy` |
| `min_warmup_bars` | `int` | `50` | Bars before signals are meaningful |
| `config_class` | `type \| None` | `None` | Frozen dataclass config class |
| `build_risk_controls` | `Callable \| None` | `None` | Factory returning list of RiskControl instances |

**Critical**: `build_strategy` must be a **factory** (callable), not an instance. Each test calls it fresh to avoid state leakage from `IndicatorPipeline._instances` caching.

## Synthetic Fixtures

Pure-math OHLCV generators — no randomness, fully deterministic:

| Function | Price Behavior | What It Tests |
|----------|---------------|---------------|
| `uptrend()` | Monotonic rise | Trending market shape |
| `downtrend()` | Monotonic decline | Trending market shape |
| `mean_reverting()` | Sine wave | Oscillating market shape |
| `flat()` | Constant price | No-movement market shape |
| `volatile_breakout()` | Flat → steep breakout | Regime change market shape |
| `gap_up()` | Trend + gap up | Stop/exit around gaps |
| `gap_down()` | Trend + gap down | Stop-loss gap behavior |

All return `pd.DataFrame` with columns `["open", "high", "low", "close", "volume"]` and a `DatetimeIndex` starting 2020-01-02.

## Contract Tests

### IndicatorSuiteContract (7 tests)

- `test_calculate_returns_dataframe` — result is pd.DataFrame
- `test_calculate_adds_columns` — new indicator columns beyond OHLCV
- `test_no_nan_after_warmup` — clean data after warmup period
- `test_preserves_ohlcv` — OHLCV columns unchanged
- `test_update_last_row_matches_calculate` — incremental == batch (live parity)
- `test_idempotent` — calculate twice → same result
- `test_runs_on_all_fixtures` — no crashes on varied market shapes

### SignalModelContract (5 tests)

- `test_generate_returns_four_keys` — {long_entry, long_exit, short_entry, short_exit}
- `test_signals_are_bool_series` — dtype bool
- `test_signal_length_matches_input` — len(signal) == len(df)
- `test_missing_columns_raises` — ValueError on missing indicators
- `test_score_entries_bounded` — finite, non-negative scores

### ConfigContract (3 tests)

- `test_defaults_instantiate` — no-arg construction works
- `test_frozen` — mutation raises FrozenInstanceError
- `test_numeric_period_params_positive` — period params > 0

All skip if `config_class is None`.

### StrategyContract (5 tests)

- `test_is_composable_strategy` — isinstance check
- `test_min_bars_required_positive` — warmup declared
- `test_full_pipeline` — indicators → signals end-to-end
- `test_score_entries_returns_series` — correct type and length
- `test_build_entry_candidate` — produces valid EntryCandidate

### LeakageContract (2 tests, parametrized) — MOST CRITICAL

- `test_no_indicator_leakage` — indicator values at bar N identical on full vs. truncated data
- `test_no_signal_leakage` — signals at bar N identical on full vs. truncated data

Parametrized across 3 offsets (10, 30, 50 bars past warmup) × 3 fixtures (uptrend, downtrend, mean_reverting) = **18 test cases**.

If any value changes when future bars are removed, the strategy has look-ahead bias.

### RiskControlContract (4 tests)

- `test_risk_controls_instantiate` — factory returns RiskControl
- `test_should_block_entry_returns_bool` — bool return, no crash
- `test_should_force_exit_returns_bool` — bool return, no crash
- `test_lifecycle_hooks_callable` — on_entry/on_exit/on_bar don't raise

All skip if `build_risk_controls is None`.

## What Each Layer Catches

| Bug | Which Contract |
|-----|---------------|
| Indicator returns wrong column names | IndicatorSuiteContract |
| NaN values leak into live calculations | IndicatorSuiteContract |
| update_last_row diverges from calculate | IndicatorSuiteContract |
| Signal dtype is float instead of bool | SignalModelContract |
| Config has negative lookback period | ConfigContract |
| Future data leaks into signals | LeakageContract |
| Refactor silently changes trade timing | LeakageContract |
| Risk control crashes on empty portfolio | RiskControlContract |

## Package Location

```
packages/algo_trading/src/prophitai_algo_trading/testing/
├── __init__.py              # Public API
├── manifest.py              # StrategyTestManifest
├── fixtures.py              # Synthetic OHLCV generators
└── contracts/
    ├── __init__.py
    ├── constants.py         # Shared constants (SIGNAL_KEYS)
    ├── indicators.py        # IndicatorSuiteContract
    ├── signals.py           # SignalModelContract
    ├── config.py            # ConfigContract
    ├── strategy.py          # StrategyContract
    ├── leakage.py           # LeakageContract
    └── risk.py              # RiskControlContract
```
