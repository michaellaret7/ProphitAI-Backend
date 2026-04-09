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

