---
date: 2026-04-09
title: Indicator constructor kwargs: ROC/SMA use window, EMA uses span
topic: coding_patterns
---
RateOfChangeIndicator (registry 'roc'): window:int=20, skip_recent:int=0, source_column:str='close', output_column:str|None=None. SimpleMovingAverageIndicator (registry 'sma'): window:int=20, source_column:str='close', output_column:str|None=None. ExponentialMovingAverageIndicator (registry 'ema'): uses 'span' NOT 'window'. Always verify kwarg names from source — EMA differs from SMA/ROC.

---
date: 2026-04-09
title: BaseIndicatorSuite: omit __init__ entirely if no config is needed
topic: framework_gotchas
---
The template's suite takes a config in __init__, but suites without config-parameterized indicators can omit __init__ entirely and just implement indicator_specs(). BaseIndicatorSuite.__init__ is inherited. For config-free suites, skip the __init__ override — the base class handles it.

---
date: 2026-04-09
title: FcfConversion pattern: merge_asof for point-in-time fundamental data
topic: coding_patterns
---
For point-in-time fundamental joins, use pd.merge_asof() with left=trading_dates Series and right=fund_avail (filing date + staleness_limit_days offset). This enforces the look-ahead barrier automatically. Pattern: set available_from = fiscal_quarter_end + staleness_limit_days, then merge_asof finds the most recent available filing per trading date. When the denominator is invalid (e.g. net_income <= 0 for FCF/NI ratio), set the output to NaN using np.where before the merge.

---
date: 2026-04-09
title: MarketStateIndicator: benchmark_close column-first lookup
topic: coding_patterns
---
For MarketStateIndicator, always check 'if benchmark_close in self.df.columns' first before falling back to df.attrs['benchmark_close']. This allows pre-joined multi-ticker DataFrames to work without attrs injection.

---
date: 2026-04-09
title: Contract tests: pytest absent, use inline Python assertions via venv python
topic: framework_gotchas
---
pytest is NOT installed in the venv and prophitai_algo_trading.testing does NOT exist. Contract tests must be written as inline Python assertion scripts invoked via /home/user/strategies/.venv/bin/python. See run_contract_tests skill for the full pattern. Do not attempt to import from prophitai_algo_trading.testing.

---
date: 2026-04-09
title: RealizedVol update_last_row needs window+1 price bars for window pct_change
topic: coding_patterns
---
RealizedVolIndicator.update_last_row() must slice -(window + 1) prices (not -window) because pct_change() consumes one extra bar. Only after dropna() do you have exactly `window` returns to compute std() from.

---
date: 2026-04-10
title: attrs stashing in suite.update_last_row — stash all non-scalar types
topic: framework_gotchas
---
When df.attrs contains a DataFrame, Series, dict, or other non-scalar, pandas combine_first inside the base pipeline's update_last_row raises 'truth value of DataFrame is ambiguous'. Fix: stash ALL non-scalar attrs before calling super().update_last_row(), restore in a finally block with 'if updated is not None' guard. Pattern: _SCALAR_TYPES = (bool, int, float, str, type(None)); stashed = {k: df.attrs.pop(k) for k, v in df.attrs.items() if not isinstance(v, _SCALAR_TYPES)}. Narrower pd.DataFrame-only check was flagged insufficient by code reviewer. Custom indicators that read attrs in update_last_row must forward-fill last value instead — if output_column in df.columns, copy prev row value to last row.

---
date: 2026-04-10
title: rolling_max IS registered in std_lib (registry key 'rolling_max')
topic: framework_gotchas
---
As of 2026-04-10, the std_lib statistical/ directory contains rolling_max.py and it IS registered with registry key 'rolling_max'. RollingMaxIndicator is importable from prophitai_algo_trading.indicators. When the manifest specifies is_custom=true for rolling max (e.g. requires min_periods=window enforcement), build a custom subclass anyway — the std_lib version uses min_periods=1 which has different NaN behavior.

---
date: 2026-04-10
title: Custom RealizedVolIndicator: use annualize/trading_days_per_year kwargs
topic: coding_patterns
---
The std_lib RealizedVolIndicator uses kwarg annualization_factor (not annualize/trading_days_per_year). When the manifest specifies those specific kwargs, build a custom subclass that accepts them. update_last_row() pattern: slice -(window+1) prices, pct_change(), dropna(), tail(window) to get exactly window clean returns, then guard len(returns) < window → NaN.

---
date: 2026-04-10
title: FcfConversion: normalize timestamps to tz-naive before merge_asof
topic: coding_patterns
---
When fundamental dates and trading index come from different sources, merge_asof fails on mixed tz-aware/tz-naive timestamps. Apply .dt.tz_localize(None).dt.normalize() to both the fund['date'] column and pd.to_datetime(self.df.index) before building the trading_dates DataFrame. Do this in _build_fundamentals() for fund dates and in calculate() for trading dates.

---
date: 2026-04-10
title: FcfConversion update_last_row: look up latest available filing, not prev row
topic: coding_patterns
---
FcfConversionIndicator.update_last_row() must query the most recent filing where available_from <= last_idx, not blindly copy the previous row value. Blind forward-fill misses a new filing that just crossed its staleness window. Pattern: last_date = pd.Timestamp(last_idx).tz_localize(None).normalize(); available = fund[fund['available_from'] <= last_date]; value = available['metric'].iloc[-1] if not available.empty else NaN.

---
date: 2026-04-14
title: Multi-quarter fundamentals: _check_fundamentals_valid helper pattern
topic: coding_patterns
---
When building a fundamentals indicator with a fundamentals_valid flag, extract a _check_fundamentals_valid(fund, n_avail) helper that (1) returns 0.0 if n_avail < MIN_QUARTERS, (2) explicitly checks that every required field is present in fund.columns (returns 0.0 if any missing), (3) checks notna().all() across the check window. Use this helper from both calculate() and update_last_row() to avoid duplicated logic and the silent bug where missing columns are skipped rather than flagged invalid. Using 'if f in check_rows.columns' in the all() generator silently passes missing fields.

---
date: 2026-04-14
title: Rolling z-score on forward-filled daily series — detect quarterly transitions
topic: coding_patterns
---
For z-scores computed on fundamental columns (forward-filled daily from quarterly filings), detect quarterly transitions by (1) dropna() to remove NaN prefix, (2) round to 10 decimal places to collapse float drift, (3) mask = rounded != rounded.shift(1); mask.iloc[0] = True to get the first bar of each new quarterly value-block. Do NOT use 'not_null != not_null.shift(1)' without rounding — float arithmetic drift creates spurious transitions on daily bars within a quarter. Then reindex back to daily with ffill.

---
date: 2026-04-16
title: Rolling z-score: shift(1) required to avoid self-inclusion in normalization
topic: coding_patterns
---
When computing a rolling z-score for a signal (e.g. per-ticker quarterly z-score), the rolling mean and std must be shifted by 1 period before computing z_raw. Pattern: roll_mean = series.rolling(window=W, min_periods=2).mean().shift(1); roll_std = series.rolling(window=W, min_periods=2).std().shift(1).fillna(0.0); z_raw = (series - roll_mean) / max(roll_std, 0.001). Without .shift(1), the current observation is included in its own normalization parameters, dampening extreme values and creating subtle look-ahead contamination within the normalization window.

---
date: 2026-04-16
title: MacroRegimeIndicator update_last_row: align exogenous series to trading index before SMA
topic: coding_patterns
---
MacroRegimeIndicator.update_last_row() must align the raw exogenous series (VIX, unemployment, etc.) to the trading index using reindex(..., method='ffill') BEFORE computing the rolling SMA — not slice the raw series directly. The full calculate() path does reindex_to_trading → rolling SMA → regime scale; the incremental path must mirror this exactly. Pattern: trading_index = pd.to_datetime(self.df.index).tz_localize(None).normalize(); series_aligned = raw_series.reindex(trading_index, method='ffill'); lookback = series_aligned.tail(window).dropna(). Slicing raw observations directly diverges from calculate() because it skips forward-fill across non-trading-day gaps.

---
date: 2026-04-16
title: Multi-quarter fundamentals_valid: fully vectorized cumsum pattern
topic: coding_patterns
---
For multi-quarter fundamental indicators, compute fundamentals_valid entirely with numpy arrays using the cumsum trick. Steps: (1) build filing_all_valid = AND of fund[f].notna().to_numpy() for all required fields — use pd.notna, NOT np.isnan which breaks on nullable/object dtypes; (2) cumsum = np.cumsum(filing_all_valid); (3) for each bar, window_sum = cumsum[end_idx] - cumsum[prev_idx] using np.where(start_idx==0, 0, cumsum[prev_idx]); (4) all_clean = window_sum == MIN_CONSECUTIVE; (5) assign via boolean masks. Eliminates the per-bar Python loop entirely. In update_last_row, always use pd.notna(val)/pd.isna(val) for scalar null checks, not np.isnan.

---
date: 2026-04-17
title: Piecewise linear regime scale: use > not >= at the halt boundary
topic: coding_patterns
---
When implementing piecewise linear regime scales (VIX, macro), use 'x > halt_threshold' (strictly above) for the 0.0 region, NOT >=. At exactly halt_threshold the scale must equal the interpolation boundary value (e.g. vix_min_scale), not 0.0. Pattern: above_halt = x > halt_threshold; in_range = (x > full_threshold) & ~above_halt. Without strict inequality, x==halt_threshold falls into the 0.0 bucket and the boundary unit test fails.

---
date: 2026-04-17
title: Multi-lag fundamental gather: O(items×lags) numpy indexing, not per-bar loop
topic: coding_patterns
---
For multi-lag fundamental indicators (q0, q4, q8 snapshots), replace a per-bar Python loop with O(items×lags) numpy operations: filing_idx = n_avail_per_bar.astype(np.int64) - 1 - lag; valid_mask = (filing_idx >= 0) & (filing_idx < n_filings); out[valid_mask] = fund_arr[filing_idx[valid_mask]]. The outer loop must be over (items × lags), not over bars. Code reviewer flags O(bars × items × lags) Python loops even when using numpy arrays inside.

---
date: 2026-04-17
title: IndicatorSpec scope="shared" is a label, not execution routing
topic: framework_gotchas
---
IndicatorSpec scope='shared' (the default) is a pipeline classification label only. It does NOT mean the indicator executes once and is shared across tickers. The orchestrator calls suite.calculate() once per ticker, so every ticker gets its own indicator execution regardless of scope. 'strategy' scope is for strategy-local override indicators. All per-ticker indicators safely use scope='shared'.

---
date: 2026-04-17
title: MacroRegimeIndicator __init__ threshold validation prevents denom=0 edge
topic: coding_patterns
---
Add __init__ validation: if halt_threshold <= full_threshold, raise ValueError. This eliminates the need for a denom==0 guard in _compute_scale() and update_last_row(). Code reviewer flags silent denom=1.0 fallback as masking misconfiguration — better to fail loudly at construction time.

---
date: 2026-04-17
title: Test fixtures: ticker in _make_fundamentals must match df.attrs['ticker']
topic: verification_failures
---
Contract test failure mode: fundamentals_valid=0.0 even with sufficient quarters. Root cause: _make_fundamentals() called with default ticker='AAAA' but df.attrs['ticker']='TEST'. Fundamentals indicators filter fund by ticker, so all rows were excluded → 0 available filings. Always pass matching ticker to _make_fundamentals(ticker='TEST') in tests, and explicitly set ticker='TEST' in both the fund DataFrame and df.attrs['ticker'].

---
date: 2026-04-17
title: Fundamental TTM rolling average: cumsum-over-filings vectorized pattern
topic: coding_patterns
---
For a fundamentals indicator computing an N-quarter TTM average after np.searchsorted(), use cumsum to avoid a per-bar Python loop: (1) nan_mask = np.isnan(metric_arr); safe_arr = np.where(nan_mask, 0.0, metric_arr); (2) cumsum = np.concatenate([[0.0], np.cumsum(safe_arr)]); valid_count_cum = np.concatenate([[0], np.cumsum(~nan_mask)]); (3) end_idx = np.minimum(n_avail_per_bar, n_filings); start_idx = np.maximum(end_idx - N_QUARTERS, 0); (4) window_sum = cumsum[end_idx] - cumsum[start_idx]; window_count = valid_count_cum[end_idx] - valid_count_cum[start_idx]; (5) enough = (n_avail_per_bar >= N_QUARTERS) & (window_count > 0); out[enough] = window_sum[enough] / window_count[enough]. Fully O(n_filings) preprocessing + O(n_bars) numpy indexing.

---
date: 2026-04-17
title: DataRequirement must cover every attrs key used in calculate() and helpers
topic: framework_gotchas
---
All DataRequirement entries must cover every key accessed via self.df.attrs inside calculate() AND every helper method called from calculate(). Missed attrs keys are a silent contract violation — the data resolver may not inject them. Audit every df.attrs.get() and df.attrs[] access in the class and declare a matching DataRequirement. If a fallback key (sector_etf_map, ticker_sector_map, benchmark_close) is part of the supported contract, it must also be declared.
---
date: 2026-04-17
title: attrs stashing in suite.update_last_row — do NOT stash if indicators need attrs
topic: framework_gotchas
---
The attrs-stashing pattern (stash non-scalar attrs before super().update_last_row()) was documented for Python 3.10/pandas < 2.x where combine_first raised 'truth value of DataFrame is ambiguous'. In Python 3.13 + current pandas, combine_first on ordinary columns does NOT raise this error. Stashing attrs BEFORE the pipeline call actively breaks indicators that need financial_ratios/fundamentals from df.attrs during their update_last_row(). DO NOT stash attrs for strategies where custom indicators read df.attrs in update_last_row(). The attrs stash is only needed if your environment actually raises the 'truth value of DataFrame is ambiguous' error — verify first with a minimal test before adding stash logic.

---
date: 2026-04-17
title: Rebalance bar: use positional trading-day-of-month, not calendar DOM
topic: coding_patterns
---
For monthly rebalance flags, group bars by (year*100+month) and mark the first N positional bars within each group — do NOT use day-of-month membership in {1,2,3,4,5} as a heuristic. The positional approach is robust to holiday calendars and correctly marks exactly N trading bars per month regardless of when they fall in the calendar. Pattern: track current_ym and count_in_month, set flag=1.0 when count_in_month <= N.

---
date: 2026-04-17
title: valuation_gate: rolling pct_rank must shift(1) like z-scores
topic: coding_patterns
---
When computing a rolling percentile rank as a gate (e.g. valuation_gate = fcf_yield_ttm rank >= 50th pctile), the shift(1) requirement applies equally to the pct_rank as to z-scores. Use fcf_yield.shift(1).rolling(window, min_periods=2).rank(pct=True) so the current bar is not included in its own rank computation. In update_last_row(), use fcf_yield.iloc[-(window+1):-1] as the lookback window before computing the percentile rank of the current value against it.

---
date: 2026-04-17
title: Constructor params must drive quarter-lag calculations, not module constants
topic: framework_gotchas
---
When an indicator has constructor params like roce_trend_years=5.0 and revenue_cagr_years=3.0, derive the quarter-lag counts from them in __init__: self._lag_roce_q = int(round(self.roce_trend_years * 4)). Do NOT use hardcoded module constants like _LAG_5YR_Q=20 in the computation methods — those make the params completely inert and create a misleading API. Code reviewer caught this: suite passes params that are ignored if you use hardcoded module-level constants inside methods. Compute derived quantities from instance attributes in __init__.

---
date: 2026-04-17
title: financial_ratios feed: single merge_asof for all ratio columns
topic: coding_patterns
---
When joining multiple TTM ratio columns from the financial_ratios feed, do a SINGLE merge_asof covering all available FMP columns at once (fr[['available_from'] + available_fmp]) rather than a separate merge_asof per column. This reduces complexity and runtime. Pattern: determine available_fmp = [c for c in _FMP_COLS if c in fr.columns]; build fr_avail = fr[['available_from'] + available_fmp].rename(...); merge once; then loop over fmp_col for clipping and assignment. Code reviewer flagged 7 separate merge_asof calls as an unnecessary duplication.

---
date: 2026-04-17
title: update_last_row ffill semantics: mirror calculate() ffill, not blind copy
topic: coding_patterns
---
For trend indicators where calculate() does ffill() on the quarterly-sampled output (carrying filing values forward daily), update_last_row() must mirror this semantics: if the vectorized point-in-time lookup returns NaN for the last bar (no new filing crossed its available_from threshold), carry forward the previous bar's value — because that previous value came from a valid earlier filing and daily persistence is correct. This is NOT blind forward-fill of stale data — it's correct filing-date propagation. The distinction: NaN from vectorized lookup means 'same filing as yesterday', not 'no data'. Code reviewer's initial concern was valid for the case where NaN means 'insufficient history', but the ffill from prev row is correct for 'no new filing'. Pattern: _ffill_or_nan helper that reads self.df[col].iloc[-2] only when the new computed value is NaN.

