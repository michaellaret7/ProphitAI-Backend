# Strategy Test Harness

Deterministic testing infrastructure for composable trading strategies. Ships with `prophitai_algo_trading` so any strategy repo gets contract tests for free.

## Purpose

The harness validates that a strategy's code **correctly implements the framework's interfaces** — not that the strategy is smart or profitable. It answers:

- Does the indicator suite produce valid, NaN-free columns after warmup?
- Does the signal model return the correct data types and shapes?
- Does the incremental update path match the batch calculation path? (live/backtest parity)
- Is the config properly frozen and immutable?
- Does the strategy use future data to make decisions? (look-ahead bias detection)
- Do custom risk controls conform to the `RiskControl` interface?

The harness is **100% strategy-agnostic**. It tests structural conformance, not trading logic. A trend-following strategy and a mean-reversion strategy inherit the exact same tests.

## Architecture

```
StrategyTestManifest (what to test)
        +
Contract Mixin Classes (how to test)
        =
Full test suite (zero bespoke code)
```

A strategy declares a single `StrategyTestManifest`. The consumer inherits from contract mixin classes. Pytest discovers all `test_*` methods from the mixins — zero bespoke test code needed.

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

Run:
```bash
pytest my_strategy/tests/test_contracts.py -v
```

## How It Works

### The Manifest

The `StrategyTestManifest` is a dataclass that tells the harness what to test. It has 5 fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | required | Human-readable strategy name (used as pytest ID) |
| `build_strategy` | `Callable[[], BaseComposableStrategy]` | required | Zero-arg factory returning a configured strategy |
| `min_warmup_bars` | `int` | `50` | Bars before indicators/signals are meaningful |
| `config_class` | `type \| None` | `None` | Frozen dataclass config class (skip config tests if None) |
| `build_risk_controls` | `Callable[[], list[RiskControl]] \| None` | `None` | Factory returning risk control instances (skip risk tests if None) |

**Critical: `build_strategy` must be a factory (callable), not an instance.** Each test method calls it fresh to avoid cross-test state leakage. The `IndicatorPipeline` caches internal state (`_instances`) after the first `calculate()` call — reusing a strategy instance across tests would cause false passes/failures.

### The Mixin Pattern

Each contract is a Python class with `test_*` methods. They are NOT standalone test classes — they are **mixins** that you inherit from. Pytest discovers the test methods through normal Python MRO (Method Resolution Order).

The mixins access the manifest via `self.manifest`, which is a class attribute set on the concrete test class. Every test method calls `self.manifest.build_strategy()` to get a fresh strategy instance.

You can inherit from any combination of mixins:

```python
# All contracts
class TestFull(IndicatorSuiteContract, SignalModelContract, ConfigContract, StrategyContract, LeakageContract, RiskControlContract):
    manifest = ...

# Just indicators and leakage (minimum viable)
class TestMinimal(IndicatorSuiteContract, LeakageContract):
    manifest = ...
```

### Synthetic Fixtures

The harness includes 7 deterministic OHLCV fixture generators. Every fixture is pure math — no randomness, no external data, same input always produces the same output.

| Function | Close Price Formula | Market Shape |
|----------|-------------------|--------------|
| `uptrend(bars=300, start=100, drift=0.002)` | `start * (1 + drift)^i` | Monotonic exponential rise |
| `downtrend(bars=300, start=100, drift=0.002)` | `start * (1 - drift)^i` | Monotonic exponential decline |
| `mean_reverting(bars=300, center=100, amplitude=10, period=40)` | `center + amplitude * sin(2*pi*i/period)` | Sine wave oscillation |
| `flat(bars=300, price=100)` | constant | Zero movement |
| `volatile_breakout(bars=300, calm_bars=200)` | flat drift → steep rise | Regime change |
| `gap_up(bars=300, gap_bar=150, gap_pct=0.05)` | trend + 5% gap up | Price gap |
| `gap_down(bars=300, gap_bar=150, gap_pct=0.05)` | trend + 5% gap down | Price gap |

All return `pd.DataFrame` with columns `["open", "high", "low", "close", "volume"]` and a business day `DatetimeIndex` starting 2020-01-02.

OHLCV relationships are guaranteed:
- `high >= max(open, close)` for every bar
- `low <= min(open, close)` for every bar
- `volume > 0` for every bar
- No NaN values anywhere

Fixtures are importable for use in custom tests:
```python
from prophitai_algo_trading.testing import uptrend, downtrend, flat, make_ohlcv
```

## Contract Tests — Detailed Reference

### IndicatorSuiteContract (7 tests)

Tests the `BaseIndicatorSuite` interface — that indicators compute correctly and consistently.

| Test | What It Validates |
|------|-------------------|
| `test_calculate_returns_dataframe` | `calculate_indicators()` returns a `pd.DataFrame` |
| `test_calculate_adds_columns` | At least one new column is added beyond the 5 OHLCV columns |
| `test_no_nan_after_warmup` | All indicator columns are NaN-free after `min_warmup_bars` |
| `test_preserves_ohlcv` | The original open/high/low/close/volume columns are unchanged |
| `test_update_last_row_matches_calculate` | The incremental `update_last_row()` path produces identical last-row values as the batch `calculate()` path |
| `test_idempotent` | Calling `calculate_indicators()` twice on the same data produces identical results |
| `test_runs_on_all_fixtures` | Parametrized across uptrend/downtrend/mean_reverting/flat — no crashes on varied market shapes |

**Why `test_update_last_row_matches_calculate` matters:** The event-driven backtest engine and the live runner use `update_last_row()` for performance (only recomputes the last bar). The batch `calculate()` is used for initial warmup. If these two paths diverge, your live trades won't match your backtest — the worst kind of bug because it's silent.

### SignalModelContract (5 tests)

Tests the `BaseSignalModel` interface — that signals have the correct structure.

| Test | What It Validates |
|------|-------------------|
| `test_generate_returns_four_keys` | `generate_signals()` returns exactly `{long_entry, long_exit, short_entry, short_exit}` |
| `test_signals_are_bool_series` | Each signal is a `pd.Series` with `dtype == bool` |
| `test_signal_length_matches_input` | Each signal series has the same length as the input DataFrame |
| `test_missing_columns_raises` | `ValueError` is raised when required indicator columns are missing from the DataFrame |
| `test_score_entries_bounded` | `score_entries()` returns finite, non-negative values |

These tests are purely structural — they verify data types and shapes, not whether the signals make good trading decisions.

### ConfigContract (3 tests)

Tests frozen dataclass config classes. All tests skip if `manifest.config_class is None`.

| Test | What It Validates |
|------|-------------------|
| `test_defaults_instantiate` | `config_class()` succeeds with no arguments (defaults work) |
| `test_frozen` | The dataclass is frozen — attribute assignment raises `FrozenInstanceError` |
| `test_numeric_period_params_positive` | Numeric fields with "period" in the name have positive default values |

### StrategyContract (5 tests)

Tests the full `BaseComposableStrategy` integration — end-to-end pipeline wiring.

| Test | What It Validates |
|------|-------------------|
| `test_is_composable_strategy` | Strategy is an instance of `BaseComposableStrategy` |
| `test_min_bars_required_positive` | `min_bars_required > 0` (every real strategy needs warmup) |
| `test_full_pipeline` | `calculate_indicators()` → `generate_signals()` runs end-to-end, produces 4 bool series |
| `test_score_entries_returns_series` | `score_entries()` returns a `pd.Series` with correct length |
| `test_build_entry_candidate` | `build_entry_candidate()` produces a valid `EntryCandidate` with correct symbol/target/price |

### LeakageContract (2 tests, parametrized = 18 cases) — MOST CRITICAL

Detects **future information leakage** (look-ahead bias). This is the single most valuable contract in the harness.

| Test | What It Validates |
|------|-------------------|
| `test_no_indicator_leakage` | Indicator values at bar N are identical whether computed on full data or truncated data (bars 0..N only) |
| `test_no_signal_leakage` | Signal values at bar N are identical on full vs. truncated data |

Each test is parametrized across:
- **3 offsets** past warmup: 10, 30, 50 bars
- **3 fixtures**: uptrend, downtrend, mean_reverting

This produces **9 cases per test = 18 total leakage checks**.

**How it works mechanically:**

```
1. Build a fresh strategy, compute indicators on full 300-bar fixture
2. Build another fresh strategy, compute indicators on truncated data (bars 0..N only)
3. Compare indicator values at bar N — they must be identical (atol=1e-10)
4. Repeat for all 4 signal keys
```

**Why two fresh strategy instances?** The `IndicatorPipeline._instances` list caches indicator objects after the first `calculate()` call. If you reuse the same strategy for the truncated run, the cache from the full run would interfere. Fresh instances guarantee the test is purely about the math.

**What triggers a failure?** Any indicator or signal that uses `df.iloc[-1]` (last row) instead of a proper rolling window, or any `shift(-n)` (forward shift), or any normalization that depends on the full series length (like `rank()` over the entire DataFrame).

### RiskControlContract (4 tests)

Tests custom `RiskControl` subclasses. All tests skip if `manifest.build_risk_controls is None`.

| Test | What It Validates |
|------|-------------------|
| `test_risk_controls_instantiate` | Each factory produces a `RiskControl` instance |
| `test_should_block_entry_returns_bool` | `should_block_entry()` returns `bool`, doesn't crash |
| `test_should_force_exit_returns_bool` | `should_force_exit()` returns `bool`, doesn't crash |
| `test_lifecycle_hooks_callable` | `on_entry()`, `on_exit()`, `on_bar()` run without raising |

Risk control tests use a **real `PortfolioTracker`** with a `FixedQuantitySizer(qty=10)` — no mocks.

## What Each Layer Catches

| Bug | Which Contract Catches It |
|-----|---------------------------|
| Indicator returns wrong column names | IndicatorSuiteContract |
| NaN values leak into live calculations | IndicatorSuiteContract |
| `update_last_row` diverges from `calculate` (live/backtest parity) | IndicatorSuiteContract |
| Indicator calculation is not idempotent | IndicatorSuiteContract |
| Signal dtype is float instead of bool | SignalModelContract |
| Signal length doesn't match input | SignalModelContract |
| Signal model crashes on missing columns | SignalModelContract |
| Config has negative lookback period | ConfigContract |
| Config is not frozen (mutable during execution) | ConfigContract |
| Strategy doesn't declare warmup requirements | StrategyContract |
| `build_entry_candidate` crashes | StrategyContract |
| Future data leaks into indicator values | LeakageContract |
| Future data leaks into signal decisions | LeakageContract |
| Refactor silently changes indicator computation | LeakageContract |
| Risk control crashes on empty portfolio | RiskControlContract |
| Risk control lifecycle hooks raise exceptions | RiskControlContract |

## What This Harness Does NOT Test

The harness is intentionally strategy-agnostic. It does **not** test:

- Whether the strategy is profitable
- Whether signals fire at the right time for a given market condition
- Whether the strategy's logic matches its design intent
- Whether parameter values are optimal
- Backtest performance metrics (Sharpe, drawdown, etc.)

These concerns belong to strategy-specific logic tests and backtesting.

## Package Location

```
packages/algo_trading/src/prophitai_algo_trading/testing/
├── __init__.py              # Public API — exports everything below
├── manifest.py              # StrategyTestManifest dataclass
├── fixtures.py              # 7 synthetic OHLCV generators + make_ohlcv helper
└── contracts/
    ├── __init__.py           # Re-exports all 6 contract classes
    ├── constants.py          # Shared SIGNAL_KEYS frozenset
    ├── indicators.py         # IndicatorSuiteContract (7 tests)
    ├── signals.py            # SignalModelContract (5 tests)
    ├── config.py             # ConfigContract (3 tests)
    ├── strategy.py           # StrategyContract (5 tests)
    ├── leakage.py            # LeakageContract (18 parametrized cases)
    └── risk.py               # RiskControlContract (4 tests)
```

## Full Example: SMA Crossover Strategy

A complete working example is at `packages/algo_trading/tests/test_harness_demo.py`. It defines a minimal SMA crossover strategy inline and runs all contracts:

```python
@dataclass(frozen=True)
class SmaCrossoverConfig:
    fast_period: int = 10
    slow_period: int = 30

class SmaCrossoverStrategy(BaseComposableStrategy):
    def __init__(self, config: SmaCrossoverConfig | None = None) -> None:
        self._config = config or SmaCrossoverConfig()
        super().__init__(
            indicator_suite=SmaCrossoverSuite(self._config),
            signal_model=SmaCrossoverSignalModel(),
        )

    @property
    def min_bars_required(self) -> int:
        return self._config.slow_period

class TestSmaCrossoverContracts(
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
):
    manifest = StrategyTestManifest(
        name="SmaCrossover",
        build_strategy=lambda: SmaCrossoverStrategy(SmaCrossoverConfig()),
        config_class=SmaCrossoverConfig,
        min_warmup_bars=30,
    )
```

Result: **41 tests pass in under 1 second.**

## API Reference

### Imports

```python
# Everything from one import
from prophitai_algo_trading.testing import (
    # Manifest
    StrategyTestManifest,
    # Fixtures
    uptrend, downtrend, mean_reverting, flat,
    volatile_breakout, gap_up, gap_down,
    make_ohlcv, OHLCV_COLS,
    # Contracts
    IndicatorSuiteContract,
    SignalModelContract,
    ConfigContract,
    StrategyContract,
    LeakageContract,
    RiskControlContract,
)
```

### Creating Custom Fixtures

Use `make_ohlcv` to create fixtures from any close price series:

```python
from prophitai_algo_trading.testing import make_ohlcv

# Custom V-shaped recovery
closes = [100 - i * 0.5 for i in range(100)] + [50 + i * 0.5 for i in range(100)]
df = make_ohlcv(closes, spread_pct=0.02, base_volume=500_000)
```
