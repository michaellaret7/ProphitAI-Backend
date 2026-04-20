---
name: enrich_month_rebalance_signal
title: Implementing Monthly Rebalance Bar Detection in enrich()
description: Use when a signal model needs an is_rebalance_bar column that fires on the Nth trading day of each calendar month
created: 2026-04-09
updated: 2026-04-20
---

## When to Use
When a signal model needs an `is_rebalance_bar` column that fires on the Nth trading day
of each new calendar month (e.g. manifest says "2nd trading day of each new month").

## Procedure

1. **Get date index as a Series** — use `df.index.to_series()` to get a DatetimeIndex-backed Series.
2. **Guard for empty df and non-DatetimeIndex** — add guards before any `.dt` access.
3. **Detect month boundaries** — compare month+year of each row to the previous row.
4. **cumsum() trick for grouping** — `new_month.cumsum()` creates a group key that increments at each new-month boundary. Name this `month_group` (NOT `intra_month_day` — code reviewer will flag the latter as misleading since it's a group key, not a day count).
5. **cumcount() for intra-month day ordinal** — `groupby(month_group).cumcount() + 1` gives the 1-indexed trading day within each month. Name this `trading_day_of_month`.
6. **Compare to offset** — `trading_day_of_month == rebalance_offset_trading_days` (default 1).
7. **Return `df.copy()`** — always copy df before adding columns to avoid mutating the caller's frame.

## Code Template
```python
def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add ``is_rebalance_bar``: True on the Nth trading day of each month.

    Requires a non-empty ``DatetimeIndex``; raises ``ValueError`` otherwise.
    """
    if df.empty:
        df = df.copy()
        df["is_rebalance_bar"] = pd.Series(dtype=bool)
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "enrich() requires a DatetimeIndex; "
            f"got {type(df.index).__name__}"
        )

    dates = df.index
    date_series = dates.to_series()

    month_values = date_series.dt.month
    year_values = date_series.dt.year

    new_month = (month_values != month_values.shift(1)) | (
        year_values != year_values.shift(1)
    )
    new_month.iloc[0] = True  # First bar is always a new month

    month_group = new_month.cumsum()  # increments at each month boundary
    trading_day_of_month = (
        date_series.groupby(month_group).cumcount() + 1
    )

    df = df.copy()
    df["is_rebalance_bar"] = (
        trading_day_of_month == self.rebalance_offset_trading_days
    )
    return df
```

## Pitfalls
- **Do NOT forget `.iloc[0] = True`** for the first bar — shift(1) produces NaN which becomes False, so the first bar won't be marked as new-month without this explicit assignment.
- **Always `df = df.copy()`** before adding columns — mutating the input df can cause subtle bugs downstream.
- **`date_series` index must match `df.index`** — using `dates.to_series()` ensures the groupby aligns properly since groupby on a Series uses its index.
- **Guard for empty df** — code reviewer flagged that `iloc[0] = True` raises on an empty frame. Always check `if df.empty:` and return early with an empty bool column.
- **Guard for non-DatetimeIndex** — if framework passes a non-datetime index, `.dt.month` raises. Check `isinstance(df.index, pd.DatetimeIndex)` and raise a clear `ValueError`.
- **Name the cumsum key `month_group`** — NOT `intra_month_day`. The cumsum result is a group key (increments at month boundaries), NOT a day count. Code reviewer flagged the misleading name in PSMO build (2026-04-20).

## Confirmed Patterns
- AQM52 (2026-04): Pattern works correctly on DatetimeIndex. Empty-df guard added after code review. All contract tests pass.
- PSMO (2026-04-20): Same pattern confirmed; variable name `month_group` preferred over `intra_month_day` per code reviewer feedback.

## Revision Log
- 2026-04-09: Created after building AQM52 signal model
- 2026-04-10: Added empty-df guard and DatetimeIndex guard after code reviewer flagged fragility
- 2026-04-20: Updated variable name recommendation: use `month_group` not `intra_month_day` for cumsum key

