# Strategy Cookbook — End-to-End

This page walks the full path from "I have an idea" to "I have a backtest result" — the same shape the reference strategy in `packages/algo_trading/tests/test_strategy/` uses.

## The 6-step recipe

1. **Define the universe + data loader.**
2. **Write the alphas** (pick the right base, implement `compute_*`).
3. **Choose / configure the PCM.**
4. **Stack risk rules in a composite.**
5. **Wire `Algorithm` + `Backtest`.**
6. **Grade the output.**

Each step below maps to a file in the reference strategy.

## 1. Universe + loader

File: `tests/test_strategy/universe.py`

Two concerns — which tickers, and how to load their history.

```python
UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", ...          # 150 liquid names
]

SECTOR_PAIRS: list[tuple[str, str]] = [
    ("KO", "PEP"), ("XOM", "CVX"), ...    # pairs for stat arb
]

START = "2023-01-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


def load_data() -> dict[str, pd.DataFrame]:
    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE, START, END, "daily")

    ready: dict[str, pd.DataFrame] = {}
    for ticker in UNIVERSE:
        df = bulk.get(ticker)
        if df is None or df.empty:
            continue
        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        ready[ticker] = df

    return ready
```

Key points:

- Drop tickers with empty frames.
- Ensure the index is a `DatetimeIndex`, sorted, deduplicated.
- Every frame has `open, high, low, close, volume` columns (lowercase).
- If you don't have DB access, use `load_csv_data` from `prophitai_algo_trading.data.csv_loader`.

## 2. Alphas

Folder: `tests/test_strategy/alphas/`

One file per alpha.  Each subclasses a base and implements only its scoring math.

### Pick the right base

| Signal shape | Base |
|--------------|------|
| Score each ticker from its own history | `PerSymbolAlpha` |
| Score each ticker against universe stats | `CrossSectionalAlpha` |
| Score ticker pairs for stat arb | `PairAlpha` |

### Example — ATR-normalized momentum (PerSymbol)

```python
from prophitai_algo_trading.alphas.base import PerSymbolAlpha


class ATRNormalizedMomentumAlpha(PerSymbolAlpha):
    name = "atr_momentum"
    required_columns = ("close", "high", "low")

    def __init__(self, return_window=20, atr_window=14, hold_days=5):
        self._return_window = return_window
        self._atr_window = atr_window
        self.hold_days = hold_days
        self.lookback = max(return_window + 1, atr_window + 1)

    def compute_score(self, symbol, df):
        closes = df["close"]
        start = float(closes.iloc[-(self._return_window + 1)])
        end = float(closes.iloc[-1])
        if start <= 0.0 or end <= 0.0:
            return None
        ret = (end / start) - 1.0

        # ATR
        prev_close = closes.shift(1).iloc[-self._atr_window:]
        high_window = df["high"].iloc[-self._atr_window:]
        low_window = df["low"].iloc[-self._atr_window:]
        true_range = pd.concat([
            high_window - low_window,
            (high_window - prev_close).abs(),
            (low_window - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = float(true_range.mean())

        if atr <= 0.0 or not np.isfinite(atr):
            return None

        atr_pct = atr / end
        if atr_pct <= 0.0:
            return None

        return ret / atr_pct
```

Read `alphas.md` for the full rules — `name` must be unique, `lookback` includes any +1 you need for diffs, `compute_score` returns `None` to skip, non-finite values are auto-filtered.

### Example — dollar-volume rank (CrossSectional)

```python
class DollarVolumeRankAlpha(CrossSectionalAlpha):
    name = "liquidity_tilt"
    required_columns = ("close", "volume")

    def __init__(self, lookback_days=20, hold_days=10, min_universe_size=5):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size
        self.lookback = lookback_days

    def compute_universe_stats(self, ctx):
        dvs = {}
        for sym, df in ctx.data.items():
            if len(df) < self.lookback:
                continue
            window = df.iloc[-self._window:]
            dv = float((window["close"] * window["volume"]).mean())
            if dv > 0 and np.isfinite(dv):
                dvs[sym] = dv

        if len(dvs) < self._min_universe:
            return None

        return {"dvs": dvs, "median_dv": float(np.median(list(dvs.values())))}

    def compute_score(self, symbol, df, stats):
        dv = stats["dvs"].get(symbol)
        if dv is None:
            return None
        return float(np.log(dv) - np.log(stats["median_dv"]))
```

The two-phase pattern (`compute_universe_stats` → `compute_score`) avoids recomputing the median per-symbol.

### Expose them from the `alphas/__init__.py`

```python
from .atr_momentum import ATRNormalizedMomentumAlpha
from .dollar_volume_rank import DollarVolumeRankAlpha
# ...

__all__ = [
    "ATRNormalizedMomentumAlpha",
    "DollarVolumeRankAlpha",
    # ...
]
```

## 3. Portfolio construction

For multi-alpha strategies, use the composite pattern: `MultiAlphaBlender` wrapping a concrete PCM.

```python
from prophitai_algo_trading.portfolio_construction import (
    MagnitudeWeightedLongShortConstructor,
    MultiAlphaBlender,
)

pcm = MultiAlphaBlender(
    weights={
        "rsi_reversion":       0.12,
        "bollinger_reversion": 0.12,
        "atr_momentum":        0.14,
        "macd_histogram":      0.12,
        "overnight_gap":       0.08,
        "liquidity_tilt":      0.08,
        "rs_rank":             0.14,
        "cointegration_pair":  0.20,
    },
    inner=MagnitudeWeightedLongShortConstructor(
        gross_exposure=1.5,
        per_position_cap=0.06,
        quantile=0.15,
        min_abs_score=0.10,
    ),
)
```

Weight-dict keys MUST match `alpha.name` values.  `Algorithm.__post_init__` enforces unique alpha names, but it does NOT validate the weight dict — a typo silently zero-weights that alpha.

Single-alpha strategies skip the blend:

```python
pcm = MagnitudeWeightedLongShortConstructor(gross_exposure=1.5)
# or
pcm = EqualWeightConstructor(max_positions=10, gross_exposure=1.0)
```

Read `portfolio_construction.md` for all four built-ins and when to use each.

## 4. Risk

Order matters in a composite: portfolio-wide circuit breakers first, position-level stops next, gross cap last.

```python
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    MaxDrawdownRiskModel,
    MaxGrossExposureRiskModel,
    StopLossExit,
)

risk = CompositeRiskModel([
    MaxDrawdownRiskModel(
        max_drawdown_pct=0.15,
        delever_factor=0.5,
        cooldown_days=30,
    ),
    StopLossExit(pct=0.08),
    MaxGrossExposureRiskModel(max_gross=1.5),
])
```

Cooking notes:

- Drop `StopLossExit` if your PCM rebalances frequently enough that stops just add whipsaw.
- Add `ReentryCooldown(bars=5)` if you see rapid re-entry churn.
- Add `ConsecutiveLossCooldown(max_losses=3, bars=20)` if the strategy goes on losing streaks.
- Add `TradingWindow(start=time(10, 0), end=time(15, 30))` for intraday strategies to avoid open/close volatility.

## 5. Wire it up — `algorithm.py` + `run.py`

File: `tests/test_strategy/algorithm.py`

```python
from prophitai_algo_trading.alphas import CointegrationPairAlpha
from prophitai_algo_trading.core.algorithm import Algorithm
from prophitai_algo_trading.execution import ExecutionModel, PortfolioSink
from .alphas import (
    ATRNormalizedMomentumAlpha, BollingerBandReversionAlpha,
    DollarVolumeRankAlpha, MACDHistogramAlpha, OvernightGapAlpha,
    RelativeStrengthRankAlpha, RSIMeanReversionAlpha,
)
from .universe import SECTOR_PAIRS


def build_algorithm() -> Algorithm:
    return Algorithm(
        alphas=[
            RSIMeanReversionAlpha(),
            BollingerBandReversionAlpha(),
            ATRNormalizedMomentumAlpha(),
            MACDHistogramAlpha(),
            OvernightGapAlpha(),
            DollarVolumeRankAlpha(),
            RelativeStrengthRankAlpha(),
            CointegrationPairAlpha(
                pairs=SECTOR_PAIRS,
                lookback_days=60,
                hold_days=10,
                entry_z=2.0,
                max_z=4.0,
            ),
        ],
        portfolio_construction=pcm,       # from step 3
        risk_management=risk,             # from step 4
        execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
    )
```

File: `tests/test_strategy/run.py`

```python
from prophitai_algo_trading import Backtest, CostModel

from .algorithm import build_algorithm
from .grading import grade
from .universe import INITIAL_CAPITAL, load_data


def main() -> None:
    data = load_data()
    algo = build_algorithm()

    engine = Backtest(
        algo,
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(ptc=0.0001, ftc=1.0),    # 1 bp + $1
    )

    result = engine.run(data)
    grade(result)


if __name__ == "__main__":
    main()
```

## 6. Grade

File: `tests/test_strategy/grading.py`

Smoke test for pipeline correctness — NOT a P&L judge.

```python
def grade(result) -> None:
    assert not result.equity_curve.empty, "equity curve is empty"
    assert (result.equity_curve["equity"] > 0).all(), "negative equity"
    assert len(result.trades) > 0, "no trades fired"

    print_metrics(result.metrics)
    print_pnl(result.equity_curve)
    print_breakdown(result.trades)

    pnl_pct = (
        result.equity_curve["equity"].iloc[-1]
        / result.equity_curve["equity"].iloc[0] - 1
    ) * 100

    # pipeline-break guard; bugs usually produce absurd results
    assert -50 < pnl_pct < 300, f"Total return {pnl_pct:+.2f}% suggests pipeline failure"
```

Once the grader passes cleanly, the plumbing is good.  Then you can iterate on strategy quality (alpha IC, turnover, Sharpe, drawdown) with confidence that it's signal-level work and not a broken pipe.

## Running

```bash
# from repo root
.venv/Scripts/python.exe packages/algo_trading/tests/test_strategy/run.py
```

(Activate the venv first: `source .venv/bin/activate`.  Always use `uv sync` to install — never `uv pip install -e`.)

## Anti-patterns to avoid

- **Don't override `update()` on an alpha base.**  `__init_subclass__` raises.  Implement `compute_score` (or `compute_universe_stats` + `compute_score`, or `compute_pair_score`).
- **Don't call `portfolio.open` / `portfolio.close` from an alpha or PCM.**  Only the sink does that, via `ExecutionModel`.
- **Don't re-implement the weight → shares math.**  Use `weight_to_shares` from the helpers.
- **Don't forget `append_close_orphans`** at the bottom of a custom PCM.  Without it, you leak stale positions when the universe changes.
- **Don't skip `load_data` sanitization.**  Duplicate timestamps and non-ascending indices silently break the backtest.
- **Don't put `MaxGrossExposureRiskModel` first** in a composite.  It should be the final guard so it sees every upstream adjustment.
- **Don't forget `name = "..."`** as a ClassVar on your alpha.  The base raises at class-definition time, but the error is at import.

## Next strategies to try

- Single-alpha with a tight stop: `MomentumAlpha()` + `MagnitudeWeightedLongShortConstructor` + `StopLossExit(0.05)`.
- Pairs-only stat arb: `CointegrationPairAlpha(pairs=SECTOR_PAIRS)` + `InsightWeightedConstructor` + `TimeStop(max_bars=30)`.
- Long-only momentum: `MomentumAlpha() + LowVolAlpha()` blended, `InsightWeightedConstructor(gross_exposure=1.0)` (no shorts), `MaxDrawdownRiskModel` + `MaxGrossExposureRiskModel(1.0)`.
