---
date: 2026-04-08
title: Cross-sectional ranking is not supported per-ticker — simplify to absolute thresholds
topic: framework_gaps
---
The framework processes each ticker independently; there is no cross-sectional groupby available at indicator or signal time. Ideas requiring sector-neutral ranking (e.g., AQM-52 top-quintile 52H rank within GICS sector) must be simplified: precompute sector-relative percentile thresholds offline and pass them in as config parameters, or use an absolute proximity threshold (e.g., 52H_ratio >= 0.90). Document this simplification in implementation_notes every time.

---
date: 2026-04-08
title: RateOfChangeIndicator default window=20 skip_recent=0 — academic momentum needs window=252 skip_recent=21
topic: constructor_gotchas
---
RateOfChangeIndicator defaults are window=20, skip_recent=0, output_column=f"roc_{window}". For 6-month momentum use window=126; for standard 12-1 month academic momentum use window=252, skip_recent=21. Always set output_column explicitly when using multiple ROC instances to avoid name collisions (e.g., output_column="roc_126" and output_column="roc_252").

---
date: 2026-04-08
title: VolatilityTargetSizer reads candidate.volatility — use std_lib RealizedVolIndicator
topic: constructor_gotchas
---
VolatilityTargetSizer.calculate_shares() reads candidate.volatility, which is populated by BaseStrategy.get_sizing_hints() only when it finds a column named exactly "volatility", "realized_vol", "close_to_close_vol_20", or "parkinson_vol_20" in the row. The std_lib RealizedVolIndicator (registry key: "realized_vol") defaults to output_column="realized_vol" which is auto-detected. Use it instead of speccing a custom indicator.

---
date: 2026-04-08
title: EarningsBlackoutControl is entry-blocker AND exit-forcer — covers both sides of earnings buffer
topic: translation_patterns
---
EarningsBlackoutControl(days=N) handles both blocking new entries AND force-exiting existing positions within N days of earnings. For AQM-52-style strategies that want "exit 2 days before, re-enter 1 day after", set days=2. The re-entry after earnings is handled by the normal monthly rebalance signal logic, not a separate control.

---
date: 2026-04-08
title: FCF conversion / fundamental quality gates require custom indicators fed from external data
topic: framework_gaps
---
The std_lib has no fundamental data indicators (FCF, net income, operating cash flow, short interest). These must be custom indicators that join pre-loaded fundamental DataFrames into the OHLCV pipeline. Spec them as custom indicators with is_custom=true and note that the coding agent must handle point-in-time data construction with a 45-day filing lag to avoid look-ahead bias.

