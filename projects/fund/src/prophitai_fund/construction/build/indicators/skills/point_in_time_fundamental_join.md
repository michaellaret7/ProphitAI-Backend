---
name: point_in_time_fundamental_join
title: Point-in-Time Fundamental Data Join for Custom Indicators
description: Use when a custom indicator needs to join quarterly fundamental data (FCF, earnings, etc.) into an OHLCV DataFrame with a look-ahead barrier (staleness gate).
created: 2026-04-09
updated: 2026-04-17
---

# Point-in-Time Fundamental Data Join for Custom Indicators

## When to Use
Any time a custom indicator must join quarterly or annual fundamental data (FCF,
earnings, book value, etc.) into the per-bar OHLCV DataFrame while enforcing a
point-in-time look-ahead barrier via a staleness / reporting-lag gate.

## Procedure

1. Retrieve the fundamentals from `df.attrs['fundamentals']` (a DataFrame with
   at least `date`, and the metric columns).
2. Guard for missing/empty fundamentals → assign NaN column and return early.
3. Copy and normalize dates to tz-naive midnight: `pd.to_datetime(fund["date"]).dt.tz_localize(None).dt.normalize()`. Also normalize the trading index in `calculate()`.
4. Compute the metric (e.g. `ocf / net_income`); use `np.where` to set NaN
   when the denominator is zero or negative.
5. Add `available_from = date + pd.Timedelta(days=staleness_limit_days)`.
6. Build `trading_dates = pd.DataFrame({'trading_date': pd.to_datetime(df.index).tz_localize(None).normalize()})`.
7. Rename `fund[['available_from', 'metric']]` → `trading_date` column; sort.
8. `pd.merge_asof(trading_dates, fund_avail, on='trading_date')` — finds the
   most recent available filing for each trading bar.
9. Set index to `trading_date`, reindex to `pd.to_datetime(df.index)`, assign
   `.values` back to `self.df[self.output_column]`.
10. Return `self.df`.

## update_last_row Pattern

Do NOT blindly forward-fill in `update_last_row()`. A new filing may have crossed
its staleness window at the current bar. Instead:

```python
def update_last_row(self, new_df):
    self.df = new_df
    last_idx = self.df.index[-1]

    fund = self._get_ticker_fundamentals()
    if fund is None:
        for col in _ALL_OUTPUT_COLUMNS:
            self.df.loc[last_idx, col] = np.nan
        return self.df

    last_date = pd.Timestamp(last_idx).tz_localize(None).normalize()
    avail = fund["available_from"].values
    n_avail = int(np.searchsorted(avail, last_date, side="right"))
    # ... assign columns at n_avail - 1 - lag indices ...
    return self.df
```

**CRITICAL: When n_avail == 0**, assign NaN/empty defaults — do NOT forward-fill
from the previous row. A bar before the first available_from date has no filing data.

**CRITICAL: For missing lags (idx out of range)**, set NaN — NOT the previous row value.
Substituting the previous row makes calculate() and update_last_row() diverge
when a new filing transitions across the available_from boundary.

## Multi-Quarter Output Pattern (q0/q2/q4 balance sheet, q0..q7 flow)

### Vectorized Indexed Gather (CORRECT — fully O(bars) per item×lag)

```python
# n_avail_per_bar = np.searchsorted(avail_arr, trading_arr, side="right")

for item in _BS_ITEMS:
    arr = fund_arrays[item]
    for lag in _BS_LAGS:
        filing_idx = n_avail_per_bar.astype(np.int64) - 1 - lag
        valid_mask = (filing_idx >= 0) & (filing_idx < n_filings)
        out = np.full(n_bars, np.nan)
        if valid_mask.any():
            out[valid_mask] = arr[filing_idx[valid_mask]]
        result[f"{item}_q{lag}"] = out
```

**CRITICAL: The outer loop must be over (items × lags), NOT over bars.**
An O(bars) Python loop that uses numpy arrays inside is still an O(bars×items×lags)
operation at scale. The correct pattern eliminates the per-bar loop entirely —
code reviewer will flag it.

### Anti-Pattern (WRONG — per-bar Python loop)
```python
for bar_i in range(len(self.df)):          # O(n_bars) Python loop — WRONG
    n_avail = int(n_avail_per_bar[bar_i])
    for item in _BS_ITEMS:
        for lag in _BS_LAGS:
            idx = n_avail - 1 - lag
            if 0 <= idx < n_filings:
                result[f"{item}_q{lag}"][bar_i] = fund_arr[idx]  # scalar access
```

## fundamentals_valid Flag Pattern

Extract a `_check_fundamentals_valid(fund, n_avail)` helper:
```python
def _check_fundamentals_valid(self, fund, n_avail):
    if n_avail < _MIN_CONSECUTIVE_QUARTERS:
        return 0.0
    required_fields = _BS_ITEMS + _FLOW_ITEMS
    for f in required_fields:
        if f not in fund.columns:  # CRITICAL: missing field → 0.0
            return 0.0
    check_rows = fund.iloc[n_avail - _MIN_CONSECUTIVE_QUARTERS : n_avail]
    for f in required_fields:
        if not check_rows[f].notna().all():
            return 0.0
    return 1.0
```
Use from both `calculate()` and `update_last_row()` to avoid duplication.
**CRITICAL**: Do NOT use `if f in check_rows.columns` inside an `all()` generator — it silently passes missing required fields instead of flagging them invalid.

### Vectorized validity via cumsum trick (for calculate())
```python
filing_all_valid = np.ones(len(fund), dtype=bool)
for f in _REQUIRED_FIELDS:
    filing_all_valid &= pd.notna(fund[f].to_numpy())
cumsum = np.cumsum(filing_all_valid.astype(np.int32))
# For each filing end_idx, window_sum = cumsum[end_idx] - (cumsum[start-1] if start>0 else 0)
# Then: validity_arr[end_idx] = window_sum == _MIN_CONSECUTIVE_QUARTERS
```

## Rolling Z-Score Pattern for Quarterly Fundamental Series

When computing per-ticker rolling z-scores on forward-filled quarterly columns:

```python
def _rolling_quarterly_zscore(series, window=8, negate=False):
    # 1. Extract quarterly transitions (first bar of each unique value block)
    not_null = series.dropna()
    rounded = not_null.round(10)  # collapse float drift
    mask = rounded != rounded.shift(1)
    mask.iloc[0] = True
    changed = not_null[mask]

    # 2. CRITICAL: shift(1) so current obs is NOT in its own normalization params
    roll_mean = changed.rolling(window=window, min_periods=2).mean().shift(1)
    roll_std = changed.rolling(window=window, min_periods=2).std().shift(1).fillna(0.0)

    # 3. z-score, clip, optional negate
    z_raw = (changed - roll_mean) / np.maximum(roll_std, 0.001)
    z = z_raw.clip(-3.0, 3.0)
    if negate:
        z = -z

    # 4. Map back to daily index via ffill
    return z.reindex(series.index, method="ffill")
```

**CRITICAL: shift(1) is mandatory.** Without it, the current observation is included
in its own rolling mean/std, which dampens extreme values and introduces look-ahead
contamination within the normalization window. This was caught by code review.

**NOTE on equal-value quarters:** The value-change detection (`rounded != rounded.shift(1)`)
misses consecutive quarters with identical values — those quarters are collapsed to
one observation. This is an acceptable approximation for financial metrics that
rarely stay identical across quarters. If exact quarter-count is critical, use an
explicit filing cadence marker (e.g., fiscal_quarter_end_date transitions) instead.

**NOTE on single-ticker requirement:** The derived-features function calling this
helper MUST be invoked on a single-ticker DataFrame only. The rolling computation
mixes ticker histories if called on a combined multi-ticker DataFrame.

## Code Template

```python
def _build_fundamentals(self) -> pd.DataFrame | None:
    fundamentals = self.df.attrs.get("fundamentals")
    if fundamentals is None or (
        isinstance(fundamentals, pd.DataFrame) and fundamentals.empty
    ):
        return None

    fund = fundamentals.copy()
    # Resolve ticker
    ticker = self.df.attrs.get("ticker")
    if ticker is not None and "ticker" in fund.columns:
        fund = fund[fund["ticker"] == ticker]
    if fund.empty:
        return None

    # CRITICAL: normalize to tz-naive to avoid mixed-tz merge_asof failures
    fund["fiscal_quarter_end_date"] = pd.to_datetime(fund["fiscal_quarter_end_date"]).dt.tz_localize(None).dt.normalize()
    fund = fund.sort_values("fiscal_quarter_end_date").reset_index(drop=True)
    fund["available_from"] = fund["fiscal_quarter_end_date"] + pd.Timedelta(days=self.filing_lag_days)
    return fund

def calculate(self) -> pd.DataFrame:
    fund = self._build_fundamentals()
    if fund is None:
        self.df[self.output_column] = np.nan
        return self.df

    # CRITICAL: normalize trading dates to match tz-naive fundamentals
    trading_dates = pd.DataFrame(
        {"trading_date": pd.to_datetime(self.df.index).tz_localize(None).normalize()}
    ).sort_values("trading_date")

    fund_avail = (
        fund[["available_from", "metric"]]
        .rename(columns={"available_from": "trading_date"})
        .sort_values("trading_date")
    )

    merged = pd.merge_asof(trading_dates, fund_avail, on="trading_date")
    merged = merged.set_index("trading_date").reindex(pd.to_datetime(self.df.index))
    self.df[self.output_column] = merged["metric"].values
    return self.df
```

## Pitfalls
- **Do NOT use `df.index` directly in merge_asof** — convert to a column first
  via `pd.to_datetime(self.df.index)` then re-align with `.reindex()`.
- **Sort both sides** before `merge_asof` or it will raise a MergeError.
- **`available_from` is the merge key** (not the raw `date`). The Timedelta
  offset IS the staleness gate.
- **Denominator guard must happen before the merge**, not after, otherwise NaN
  propagation is lost when merge forward-fills.
- **Return `.values`** when assigning back: `merged["metric"].values` avoids
  index-alignment surprises.
- **ALWAYS normalize timestamps to tz-naive** on BOTH sides before merge_asof.
- **update_last_row must look up the latest available filing**, NOT blindly
  forward-fill the previous row.
- **update_last_row n_avail==0 → assign NaN defaults, NOT previous row forward-fill.**
- **update_last_row missing lags → NaN, NOT previous row copy.**
- **_check_fundamentals_valid MUST explicitly guard missing fields**: use a for-loop
  with `if f not in fund.columns: return 0.0`, NOT `if f in cols` in a generator.
- **Rolling z-score MUST shift(1)**: current observation must not appear in its own
  rolling mean/std — shift() ensures normalization uses only prior observations.
- **Per-ticker only**: derived-features function with rolling z-scores must only
  be called with a single-ticker DataFrame.
- **VIX piecewise scale: use `>` not `>=` for halt_threshold**: at exactly
  halt_threshold the scale should equal vix_min_scale (the interpolation boundary),
  not 0.0. Use `above_halt = vix > halt_threshold` (strictly above).

## Confirmed Patterns
- FcfConversionIndicator (AQM52) — single metric output.
- CCCFundamentalsIndicator (WVCCI) — multi-quarter output (q0..q7 flow, q0/q2/q4 BS).
  Uses np.searchsorted on available_from array for O(log n) per-bar lookup.
  Uses _check_fundamentals_valid helper called from both calculate() and update_last_row().
  Vectorized indexed gather: outer loop over (items×lags), inner numpy fancy indexing.
- Rolling z-score with shift(1) (WVCCI) — quarterly z-score on forward-filled daily series.
- NaN flags for boolean derived columns: use np.nan (not 0.0) when inputs are missing
  — prevents "unknown data" from being encoded as "false" in the signal model.
- Named module-level constants for derived-feature thresholds (e.g. _DPO_ABSOLUTE_CAP_DAYS)
  instead of inline literals — caught by code reviewer as maintainability issue.

## Revision Log
- 2026-04-09: Created after building FcfConversionIndicator for AQM52 strategy.
- 2026-04-10: Added tz-normalization pitfall. Added correct update_last_row pattern.
- 2026-04-14: Added multi-quarter output pattern (WVCCI). Added _check_fundamentals_valid
  helper pattern with critical missing-column guard. Added np.searchsorted approach for
  efficient per-bar filing lookup without merge_asof (useful when output is many columns).
- 2026-04-16: Added rolling z-score pattern with shift(1) — CRITICAL to avoid self-inclusion
  in normalization. Confirmed in WVCCI build and caught by code review.
- 2026-04-16: Added CRITICAL update_last_row NaN policy pitfalls (n_avail==0 and
  missing lags must assign NaN, NOT forward-fill from previous row). Added per-ticker
  single-ticker requirement for derived-features function. Added NaN-flag best practice.
- 2026-04-17: Added fully vectorized indexed gather pattern for multi-lag indicators
  (outer loop over items×lags, inner numpy fancy indexing). Clarified anti-pattern
  (per-bar Python loop). Added VIX piecewise scale `>` vs `>=` pitfall.
  Added named module-level constants for hardcoded thresholds (reviewer finding).

