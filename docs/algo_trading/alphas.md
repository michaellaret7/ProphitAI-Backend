# Alphas — Authoring a Signal

An alpha is a function from per-bar market data to a list of `Insight`s.  Three base classes in `alphas/base.py` cover ~100% of patterns — pick the one that matches your signal's semantics, and implement ONLY the `compute_*` hook.

```
PerSymbolAlpha         score each ticker independently
CrossSectionalAlpha    score each ticker vs. universe stats
PairAlpha              score ticker pairs for stat-arb
```

All three satisfy the `AlphaModel` protocol.  **Do not override `update()`** — the base owns pipeline semantics, and `__init_subclass__` raises if you do.

## Subclass contract — universal

Every alpha subclass must set these:

| Attribute | Type | Meaning |
|-----------|------|---------|
| `name` | `str` (ClassVar) | Unique identifier.  `MultiAlphaBlendPCM` partitions insights by this — must match the key in its `weights` dict. |
| `lookback` | `int` | Bars of history required before `update()` emits.  Engines skip alpha until this is met. |
| `hold_days` | `int` | Informational `close_time` horizon. `PerSymbolAlpha` / `CrossSectionalAlpha` / `PairAlpha` use this to set `Insight.close_time = ctx.timestamp + timedelta(days=hold_days)`. |
| `required_columns` | `tuple[str, ...]` (ClassVar) | OHLCV columns this alpha needs.  Default `("close",)`.  Frames missing any column are filtered out before your `compute_*` runs. |

## Robustness guarantees (all three bases)

The base owns these before calling your hook — you don't re-implement them:

1. **Symbol arg** — passed to every `compute_*` so you can do ticker-conditional logic.
2. **Required-columns filter** — frames missing any column in `required_columns` are skipped silently.
3. **Lookback filter** — frames with `len(df) < lookback` are skipped.
4. **NaN / Inf guard** — non-finite scores are treated as `None` (skip).
5. **Class-definition check** — `name: str` must be set, `update` must not be overridden.
6. **Instance preflight** — first `update()` validates `lookback > 0`, `hold_days > 0`, non-empty `required_columns` (and non-empty, non-self, non-duplicate `pairs` for `PairAlpha`).

## `PerSymbolAlpha` — the default

Score each ticker from its own history alone.  Covers momentum, breakout, RSI, MACD, single-ticker fundamentals — anything where "this symbol is going up/down" makes sense without looking at the rest of the universe.

```python
class PerSymbolAlpha(ABC):
    name: str               # ClassVar
    lookback: int           # instance
    hold_days: int          # instance
    required_columns: tuple[str, ...] = ("close",)  # ClassVar, override if needed

    @abstractmethod
    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None: ...
```

### `compute_score` contract

- **Return a signed float**: positive = long, negative = short, 0 = flat.
- Return `None` to skip this symbol (missing data, degenerate sample, bad price).
- `None` / NaN / Inf are all treated as "skip".
- The base maps the sign to `direction` and uses `abs(score)` as `magnitude`.

### Example: the built-in `MomentumAlpha`

```python
class MomentumAlpha(PerSymbolAlpha):
    name = "momentum"

    def __init__(self, lookback_days=252, skip_days=21, hold_days=5):
        self._lookback_days = lookback_days
        self._skip_days = skip_days
        self.hold_days = hold_days
        self.lookback = lookback_days + 1       # need lookback+1 closes

    def compute_score(self, symbol, df):
        closes = df["close"]
        start = float(closes.iloc[-(self._lookback_days + 1)])
        end = float(closes.iloc[-(self._skip_days + 1)])

        if start <= 0.0 or end <= 0.0:
            return None

        return (end / start) - 1.0
```

### Example: multi-column alpha

```python
class OvernightGapAlpha(PerSymbolAlpha):
    name = "overnight_gap"
    required_columns = ("open", "close")     # the base will skip frames missing either

    def __init__(self, lookback_days=20, hold_days=3):
        self._window = lookback_days
        self.hold_days = hold_days
        self.lookback = lookback_days + 1

    def compute_score(self, symbol, df):
        overnight = (df["open"] / df["close"].shift(1) - 1.0).iloc[-self._window:].dropna()

        if len(overnight) < self._window // 2:
            return None

        return float(overnight.mean())
```

## `CrossSectionalAlpha` — universe-wide stats

Score each ticker against universe-wide statistics (median, rank, percentile).  Covers low-vol anomaly, rank-based L/S, size/value factors, dispersion signals — anything where "this symbol is going up" only means something **relative to the universe**.

```python
class CrossSectionalAlpha(ABC):
    name: str
    lookback: int
    hold_days: int
    required_columns: tuple[str, ...] = ("close",)

    @abstractmethod
    def compute_universe_stats(self, ctx: AlgorithmContext) -> Any: ...

    @abstractmethod
    def compute_score(self, symbol: str, df: pd.DataFrame, stats: Any) -> float | None: ...
```

### Two-phase update

Per bar:

1. **`compute_universe_stats(ctx)`** runs ONCE across the universe.  Return whatever shape you need (dict, tuple, namedtuple).  Return `None` to signal "universe not ready this bar" — the base emits an empty list.
2. **`compute_score(symbol, df, stats)`** runs PER ticker using the precomputed stats.

This split avoids recomputing the median/rank/percentile once per symbol.

### Example: the built-in `LowVolAlpha`

```python
class LowVolAlpha(CrossSectionalAlpha):
    name = "low_vol"

    def __init__(self, lookback_days=60, hold_days=20, min_universe_size=3):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size
        self.lookback = lookback_days + 1

    def compute_universe_stats(self, ctx):
        sigmas = {}
        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue
            sigma = _realized_sigma(df["close"], self._window)
            if sigma is None:
                continue
            sigmas[symbol] = sigma

        if len(sigmas) < self._min_universe:
            return None

        return {"sigmas": sigmas, "median": float(np.median(list(sigmas.values())))}

    def compute_score(self, symbol, df, stats):
        sigma = stats["sigmas"].get(symbol)
        if sigma is None:
            return None
        return stats["median"] - sigma   # positive = below-median = long
```

## `PairAlpha` — stat arb

Score ticker **pairs**.  Each firing pair emits TWO `Insight`s with opposite directions and equal magnitude — dollar-neutral by construction.

```python
class PairAlpha(ABC):
    name: str
    lookback: int
    hold_days: int
    pairs: list[tuple[str, str]]     # instance attr — set in __init__
    required_columns: tuple[str, ...] = ("close",)

    @abstractmethod
    def compute_pair_score(
        self,
        sym_a: str,
        sym_b: str,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
    ) -> float | None: ...
```

### `compute_pair_score` contract

- Positive score → long A / short B.
- Negative score → short A / long B.
- `None` / NaN / Inf → skip this pair.

The base emits:

```python
Insight(symbol=sym_a, direction=+1 if score > 0 else -1, magnitude=abs(score), ...)
Insight(symbol=sym_b, direction=-1 if score > 0 else +1, magnitude=abs(score), ...)
```

### `pairs` validation

At first `update()`, the base rejects:

- Empty `pairs`.
- Self-pairs `(A, A)`.
- Duplicates (pair uniqueness is order-independent — `(A, B)` and `(B, A)` collide).

### Example: the built-in `CointegrationPairAlpha`

See `alphas/cointegration_pair.py` for a full OLS-hedged z-score implementation.  The shape:

```python
class CointegrationPairAlpha(PairAlpha):
    name = "cointegration_pair"

    def __init__(self, pairs, lookback_days=60, hold_days=10, entry_z=2.0, max_z=4.0):
        ...
        self.pairs = list(pairs)
        self.lookback = lookback_days
        self.hold_days = hold_days

    def compute_pair_score(self, sym_a, sym_b, df_a, df_b):
        # OLS regress log(A) on log(B), z-score the residual, clip, negate.
        ...
```

## When none of the three fit

If your alpha needs something that doesn't map to these patterns (event streams, external side-channel data, state shared across alphas), implement the `AlphaModel` protocol directly:

```python
class MyExoticAlpha:
    name = "exotic"
    lookback = 0

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        ...
```

The `Protocol` is the only real contract — the bases are just templates that eliminate the repetition.

## Multi-alpha considerations

- **`name` must be unique across all alphas in an `Algorithm`.**  `Algorithm.__post_init__` raises on duplicates.
- When two alphas emit for the same symbol, `MultiAlphaBlendPCM` blends them; PCMs that take one insight per symbol call `dedupe_insights(insights)` which keeps the highest `|direction * magnitude|`.
- `source_alpha` on the emitted `Insight` is auto-set from `self.name` by all three bases — don't set it manually.

## Built-in alphas (reference)

| Class | Base | Default lookback | What it measures |
|-------|------|------------------|------------------|
| `MomentumAlpha` | PerSymbol | 253 | 12-1 price momentum (Jegadeesh-Titman) |
| `BreakoutAlpha` | PerSymbol | 20 | Donchian channel position |
| `ShortTermReversalAlpha` | PerSymbol | 6 | Negated N-day return |
| `TrendVolumeAlpha` | PerSymbol | 35 | MACD histogram × volume z-score |
| `LowVolAlpha` | CrossSectional | 61 | Median-centered realized vol (low vol → long) |
| `CointegrationPairAlpha` | Pair | 60 | OLS-hedged log-spread z-score |

Additional reference implementations live in `packages/algo_trading/tests/test_strategy/alphas/` — RSI reversion, Bollinger reversion, ATR momentum, MACD histogram, overnight gap, dollar-volume rank, RS rank.
