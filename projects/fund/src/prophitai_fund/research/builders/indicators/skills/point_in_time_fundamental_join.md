---
name: point_in_time_fundamental_join
title: Point-in-Time Fundamental Data Join for Custom Indicators
description: Use when a custom indicator needs to join quarterly fundamental data (FCF, earnings, etc.) into an OHLCV DataFrame with a look-ahead barrier (staleness gate).
created: 2026-04-09
updated: 2026-04-09
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
3. Copy and `pd.to_datetime` the `date` column; `sort_values`.
4. Compute the metric (e.g. `ocf / net_income`); use `np.where` to set NaN
   when the denominator is zero or negative.
5. Add `available_from = date + pd.Timedelta(days=staleness_limit_days)`.
6. Build `trading_dates = pd.DataFrame({'trading_date': pd.to_datetime(df.index)})`.
7. Rename `fund[['available_from', 'metric']]` → `trading_date` column; sort.
8. `pd.merge_asof(trading_dates, fund_avail, on='trading_date')` — finds the
   most recent available filing for each trading bar.
9. Set index to `trading_date`, reindex to `pd.to_datetime(df.index)`, assign
   `.values` back to `self.df[self.output_column]`.
10. Return `self.df`.

## Code Template

```python
def calculate(self) -> pd.DataFrame:
    fundamentals = self.df.attrs.get("fundamentals")
    if fundamentals is None or (
        isinstance(fundamentals, pd.DataFrame) and fundamentals.empty
    ):
        self.df[self.output_column] = np.nan
        return self.df

    fund = fundamentals.copy()
    fund["date"] = pd.to_datetime(fund["date"])
    fund = fund.sort_values("date").reset_index(drop=True)

    # Compute ratio; NaN when denominator <= 0
    fund["metric"] = np.where(
        fund["net_income_ttm"] > 0,
        fund["operating_cash_flow_ttm"] / fund["net_income_ttm"],
        np.nan,
    )

    # Point-in-time gate: filing not visible until staleness_limit_days after quarter-end
    fund["available_from"] = fund["date"] + pd.Timedelta(days=self.staleness_limit_days)

    trading_dates = pd.DataFrame(
        {"trading_date": pd.to_datetime(self.df.index)}
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

## Confirmed Patterns
- FcfConversionIndicator (AQM52) — uses this pattern exactly; passes smoke test
  with 300 bars synthetic data and 8 quarterly filings.
- `update_last_row` for these indicators is cheaply delegated to `self.calculate()`
  since fundamental data rarely changes intraday.

## Revision Log
- 2026-04-09: Created after building FcfConversionIndicator for AQM52 strategy.

