# Universe indicator cross-sectional caching

## Problem

Universe-scoped indicators (sector-neutral z-scores, cross-sectional rank,
dispersion regimes, factor-risk models) share a single computation: they
build a full `(date × ticker)` panel of cross-sectional values, then each
ticker reads its own slice.

The vectorized engine re-instantiates the indicator once per ticker
(`generate_vectorized_signals` loops `for ticker in tickers:
strategies[ticker].calculate_indicators(real_data)`). A naive universe
indicator rebuilds the full panel on every call — the result is identical
for every ticker in the run, but the per-ticker cost is O(n × bars).
Total work is O(n² × bars).

**Measured cost on RLS-DB at n=36 tickers, 5y daily:** the universe
indicator called `calculate` 36 times at ~2.6s each → 93s of `engine.run`
total, of which 90s was recomputing identical cross-sectional output.

Projected at n=220: ~58 minutes.

## Solution: stamped panel + framework cache

`packages/algo_trading/src/prophitai_algo_trading/indicators/cross_sectional_cache.py`
provides three helpers:

- `stamp_shared_panel(panel)` — attach a run-scoped UUID to `panel.attrs`
  *before* the panel is attached to per-ticker `df.attrs`. The UUID is
  immutable (`copy.deepcopy` treats strings as atomic) so it survives
  pandas `__finalize__` deep-copies during `reindex` / `.copy()` /
  `.drop()`. **Without the stamp, every ticker sees a freshly copied
  panel with a new `id(...)` and the cache misses 100%.**

- `crosssectional_cache_key(panel, *params)` — builds a hashable key
  from the stamped UUID plus indicator parameters. Different params
  (different dispersion windows, winner quantiles, etc.) get independent
  cache entries.

- `get_or_compute_crosssectional(key, compute)` — cache-aside wrapper
  with bounded size (4 entries, cleared en-bloc). Returns the cached
  result or invokes `compute()` on miss.

## Usage pattern

### 1. Panel construction

If the panel is fetched by a `DataResolver` provider with `scope="shared"`
and the provider returns a `pd.DataFrame`, **the resolver auto-stamps**
— no action needed.

If the panel is built by a strategy-local helper (like
`attach_screener_attrs` on RLS-DB), stamp it explicitly:

```python
from prophitai_algo_trading.indicators import stamp_shared_panel

panel = build_cross_sectional_panel(...)
stamp_shared_panel(panel)

for ticker_df in data.values():
    ticker_df.attrs["my_panel"] = panel
```

### 2. Universe indicator

Split the indicator into `_compute_full_crosssectional(panel) -> DataFrame`
(universe-wide, expensive, cached) and `calculate()` (per-ticker slice,
cheap, not cached):

```python
from prophitai_algo_trading.indicators import (
    BaseIndicator,
    crosssectional_cache_key,
    get_or_compute_crosssectional,
)


class MyUniverseIndicator(BaseIndicator):
    def _compute_full_crosssectional(self, panel: pd.DataFrame) -> pd.DataFrame:
        # ALL sector groupbys, cross-sectional ranks, rolling dispersion,
        # etc. Returns the full (date × ticker) panel with every output
        # column populated.
        ...

    def calculate(self) -> pd.DataFrame:
        raw_panel = self.df.attrs.get("my_panel")
        cache_key = crosssectional_cache_key(
            raw_panel, self.window, self.quantile, ...  # all params
        )

        full = get_or_compute_crosssectional(
            cache_key,
            lambda: self._compute_full_crosssectional(self._build_panel()),
        )

        if full.empty:
            # NaN-fill and return
            ...

        # Per-ticker slice — cheap, not cached
        symbol, _ = _get_symbol_and_sector(self.df)
        my_rows = full[full["symbol"] == symbol].sort_values("date").set_index("date")
        aligned = my_rows.reindex(_safe_normalize_index(self.df.index)).ffill()
        for column in self.output_columns:
            self.df[column] = aligned[column].to_numpy(dtype=float, copy=False)

        return self.df
```

## Measured speedup

RLS-DB strategy, 36 tickers × 5y daily, local Mac:

| Variant | `engine.run` | total |
|---|---|---|
| Unpatched | **93.05s** | 107.62s |
| Framework cache | **18.21s** | 42.71s |

**5.1× speedup on `engine.run`, 2.5× on total wall clock.** First ticker
pays the full cost (~15s), remaining 35 tickers take ~3s combined.

Projected at n=220: **~3 min total** (down from a projected ~58 min
without the cache).

## Invariants / gotchas

- **Stamp the panel BEFORE attaching to per-ticker `df.attrs`.** Pandas
  `__finalize__` deep-copies `attrs` on every reindex/copy, but strings
  in the attrs dict are preserved (immutable atoms). If you stamp after
  attach and the strategy then copies the frame, only some copies will
  carry the UUID.
- **Include every indicator parameter in the cache key.** Two indicator
  instances with different params must NOT share a cached panel, or
  you'll read the wrong output.
- **Don't mutate the cached DataFrame.** `get_or_compute_crosssectional`
  returns the same object for every cache hit — if a ticker writes back
  to it, subsequent tickers see the mutation. Slice out your per-ticker
  data into a new frame instead of modifying the shared one.
- **Cache lives at module-level and persists across backtest runs in the
  same process.** Different runs get different stamps, so no collision.
  Call `clear_crosssectional_cache()` in tests that mutate or in
  long-running servers between runs.
