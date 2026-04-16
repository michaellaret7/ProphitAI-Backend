---
date: 2026-04-09
title: ROC and SMA exact kwarg names verified
topic: coding_patterns
---
RateOfChangeIndicator (registry key "roc"): __init__ params are window:int=20, skip_recent:int=0, source_column:str="close", output_column:str|None=None. SimpleMovingAverageIndicator (registry key "sma"): __init__ params are window:int=20, source_column:str="close", output_column:str|None=None. ExponentialMovingAverageIndicator (registry key "ema"): uses "span" not "window". Always verify kwarg names — EMA uses span, SMA uses window.

---
date: 2026-04-09
title: BaseIndicatorSuite: no config required in __init__ if not needed
topic: framework_gotchas
---
The template's TemplateIndicatorSuite takes a config in __init__. But if your suite doesn't need a config object, you can omit __init__ entirely and just implement indicator_specs(). BaseIndicatorSuite.__init__ is called via super().__init__() in the template config example. For config-free suites, just skip __init__ override — the base class handles it.

---
date: 2026-04-09
title: No rolling_max in std_lib — always use custom indicator
topic: framework_gotchas
---
The std_lib statistical/ directory only contains zscore.py. There is no rolling_max indicator in the registry. Any rolling-max requirement must be implemented as a custom BaseIndicator subclass. std_lib coverage: sma, ema, rsi, macd, adx, roc, atr, bollinger_bands, bollinger_pct_b, donchian_channels, obv, vwap, zscore.

---
date: 2026-04-09
title: FcfConversion pattern: merge_asof for point-in-time fundamental data
topic: coding_patterns
---
For point-in-time fundamental joins, use pd.merge_asof() with left=trading_dates Series and right=fund_avail (filing date + staleness_limit_days offset). This enforces the look-ahead barrier automatically. Key: set available_from = fiscal_quarter_end + staleness_limit_days, then merge_asof finds the most recent available filing per trading date. When net_income <= 0, set fcf_conversion to NaN using np.where before the merge.

---
date: 2026-04-09
title: AQM52: IndicatorSpec scope field confirmed valid
topic: framework_gotchas
---
IndicatorSpec dataclass has a `scope` field of type Literal["shared", "strategy"] defaulting to "shared". It is safe to pass scope="shared" in all specs — confirmed in specs.py from the installed package.

---
date: 2026-04-09
title: MarketStateIndicator: benchmark_close column-first lookup
topic: coding_patterns
---
For MarketStateIndicator, always check `if 'benchmark_close' in self.df.columns` first before falling back to `df.attrs['benchmark_close']`. This allows pre-joined multi-ticker DataFrames to work without attrs injection.

---
date: 2026-04-09
title: run_contract_tests skill: testing module absent in current package install
topic: framework_gotchas
---
The `prophitai_algo_trading.testing` module (StrategyTestManifest, IndicatorSuiteContract, LeakageContract) is NOT present in the installed package in the sandbox as of 2026-04-09. The run_contract_tests skill procedure fails at import. Fall back to running manual functional smoke tests + leakage checks via sandbox_bash Python scripts instead.

---
date: 2026-04-09
title: RealizedVol: update_last_row needs window+1 price bars for window pct_change
topic: coding_patterns
---
RealizedVolIndicator.update_last_row() must slice `-(window + 1)` prices (not `-window`) because pct_change() consumes one extra bar. Only after dropna() do you have exactly `window` returns to compute std() from.

---
date: 2026-04-10
title: attrs stashing in suite.update_last_row for pandas combine_first
topic: framework_gotchas
---
When df.attrs contains a DataFrame (e.g. 'fundamentals'), pandas combine_first inside the base pipeline's update_last_row raises "truth value of DataFrame is ambiguous". Fix: stash non-scalar attrs before calling super().update_last_row(), restore in a finally block with `if updated is not None` guard. Custom indicators that read attrs in update_last_row must forward-fill last value instead — FcfConversionIndicator pattern: if output_column in df.columns, copy prev row value to last row.

---
date: 2026-04-10
title: RollingMaxIndicator: std_lib now has rolling_max registered
topic: framework_gotchas
---
As of 2026-04-10, the std_lib statistical/ directory DOES contain rolling_max.py and it IS registered with registry key "rolling_max". RollingMaxIndicator is importable from prophitai_algo_trading.indicators. Memory entry from 2026-04-09 was incorrect. When the manifest specifies is_custom=true for rolling max (with min_periods=window enforcement), build a custom class anyway — the std_lib version uses min_periods=1 which has different NaN behavior.

---
date: 2026-04-10
title: RealizedVolIndicator: custom kwarg name is annualize/trading_days_per_year
topic: coding_patterns
---
The std_lib RealizedVolIndicator uses kwarg annualization_factor (not annualize/trading_days_per_year). When manifest specifies those specific kwargs, build a custom subclass that accepts them. The update_last_row() pattern: slice -(window+1) prices, pct_change(), dropna(), tail(window) to get exactly window clean returns, then guard len(returns) < window → NaN.

---
date: 2026-04-10
title: FcfConversion: normalize timestamps to tz-naive before merge_asof
topic: coding_patterns
---
When fundamental dates and trading index come from different sources, merge_asof fails on mixed tz-aware/tz-naive timestamps. Fix: apply .dt.tz_localize(None).dt.normalize() to both the fund["date"] column and pd.to_datetime(self.df.index) before building the trading_dates DataFrame. Do this in _build_fundamentals() for fund dates and in calculate() for trading dates.

---
date: 2026-04-10
title: FcfConversion update_last_row: look up latest available filing, not prev row
topic: coding_patterns
---
FcfConversionIndicator.update_last_row() must query the most recent filing where available_from <= last_idx, not blindly copy the previous row value. Blind forward-fill misses a new filing that just crossed its staleness window. Use: last_date = pd.Timestamp(last_idx).tz_localize(None).normalize(); available = fund[fund['available_from'] <= last_date]; value = available['metric'].iloc[-1] if not available.empty else NaN.

---
date: 2026-04-14
title: Multi-quarter fundamental indicator: _check_fundamentals_valid helper pattern
topic: coding_patterns
---
When building a fundamentals indicator with a fundamentals_valid flag, extract a `_check_fundamentals_valid(fund, n_avail)` helper that: (1) returns 0.0 if n_avail < MIN_QUARTERS, (2) explicitly checks that every required field is present in fund.columns (returning 0.0 if any missing), (3) checks notna().all() across the check window. Use this helper from both calculate() and update_last_row() to avoid duplicated logic and the silent bug where missing columns are skipped rather than flagged invalid. Using `if f in check_rows.columns` in the all() generator silently passes missing fields.

---
date: 2026-04-14
title: Rolling z-score on forward-filled daily series: quarterly transition detection
topic: coding_patterns
---
For z-scores computed on fundamental columns (forward-filled daily from quarterly filings), detect quarterly transitions by: (1) dropna() to remove NaN prefix, (2) round to 10 decimal places to collapse float drift, (3) `mask = rounded != rounded.shift(1); mask.iloc[0] = True` to get the first bar of each new quarterly value-block. Do NOT use `not_null != not_null.shift(1)` without rounding — float arithmetic drift can create spurious transitions on daily bars within a quarter. Then reindex back to daily with ffill.

---
date: 2026-04-16
title: Rolling z-score: shift(1) required to avoid self-inclusion in normalization
topic: coding_patterns
---
When computing a rolling z-score for a signal (e.g., per-ticker quarterly z-score), the rolling mean and std must be shifted by 1 period before computing z_raw. Pattern: roll_mean = series.rolling(window=W, min_periods=2).mean().shift(1); roll_std = series.rolling(window=W, min_periods=2).std().shift(1).fillna(0.0); z_raw = (series - roll_mean) / max(roll_std, 0.001). Without .shift(1), the current observation is included in its own normalization parameters, which dampens extreme values and creates subtle look-ahead contamination within the normalization window. This was caught by code review on WVCCI.

---
date: 2026-04-16
title: MacroRegimeIndicator update_last_row: align VIX to trading index before SMA
topic: coding_patterns
---
MacroRegimeIndicator.update_last_row() must align the raw VIX series to the trading index (using reindex(..., method='ffill')) BEFORE computing the rolling SMA — not slice the raw VIX directly. The full calculate() path does: reindex_to_trading → rolling SMA → regime scale. The incremental path must mirror this exactly. If update_last_row slices raw VIX observations (skipping non-VIX days), it diverges from calculate() which forward-fills VIX across non-trading-day gaps first. Fix: trading_index = pd.to_datetime(self.df.index).tz_localize(None).normalize(); vix_aligned = vix_series.reindex(trading_index, method='ffill'); lookback = vix_aligned.tail(window).dropna().

