---
name: point_in_time_fundamental_join
title: Point-in-Time Fundamental Data Join for Custom Indicators
description: Use when a custom indicator needs to join quarterly fundamental data (FCF, earnings, etc.) into an OHLCV DataFrame with a look-ahead barrier (staleness gate).
created: 2026-04-09
updated: 2026-04-10
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

    fund = self._build_fundamentals()
    if fund is None:
        # carry forward prev value or NaN
        ...
        return self.df

    last_date = pd.Timestamp(last_idx).tz_localize(None).normalize()
    available = fund[fund["available_from"] <= last_date]
    if available.empty:
        self.df.loc[last_idx, self.output_column] = float("nan")
    else:
        self.df.loc[last_idx, self.output_column] = available["metric"].iloc[-1]
    return self.df
```

## Code Template

```python
def _build_fundamentals(self) -> pd.DataFrame | None:
    fundamentals = self.df.attrs.get("fundamentals")
    if fundamentals is None or (
        isinstance(fundamentals, pd.DataFrame) and fundamentals.empty
    ):
        return None

    fund = fundamentals.copy()
    # CRITICAL: normalize to tz-naive to avoid mixed-tz merge_asof failures
    fund["date"] = pd.to_datetime(fund["date"]).dt.tz_localize(None).dt.normalize()
    fund = fund.sort_values("date").reset_index(drop=True)

    fund["metric"] = np.where(
        fund["net_income_ttm"] > 0,
        fund["operating_cash_flow_ttm"] / fund["net_income_ttm"],
        np.nan,
    )
    fund["available_from"] = fund["date"] + pd.Timedelta(days=self.staleness_limit_days)
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
  `pd.to_datetime(fund["date"]).dt.tz_localize(None).dt.normalize()` for fund dates,
  `pd.to_datetime(self.df.index).tz_localize(None).normalize()` for trading dates.
  Mixed tz-aware/naive comparisons crash at runtime.
- **update_last_row must look up the latest available filing**, NOT blindly
  forward-fill the previous row. A new filing may have crossed the staleness
  window at the current bar. Use the `_build_fundamentals()` helper and filter
  `fund[fund["available_from"] <= last_date]`.

## Confirmed Patterns
- FcfConversionIndicator (AQM52) — uses this pattern exactly; passes smoke test
  with 300 bars synthetic data and 8 quarterly filings.
- `_build_fundamentals()` helper is key — called by both `calculate()` and
  `update_last_row()`, avoiding duplication of the normalization and ratio logic.

## Revision Log
- 2026-04-09: Created after building FcfConversionIndicator for AQM52 strategy.
- 2026-04-10: Added tz-normalization pitfall (both sides of merge_asof must be
  tz-naive). Added correct update_last_row pattern (query latest available filing
  rather than forward-filling prev row). Added _build_fundamentals() helper pattern.

