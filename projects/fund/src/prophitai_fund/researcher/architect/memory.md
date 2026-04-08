---
date: 2026-04-08
title: Rolling-max / 52-week-high requires custom indicator
topic: framework_gaps
---
No std_lib indicator computes a rolling maximum of the close price (needed for 52-week-high proxy). DonchianChannelsIndicator uses rolling-max of the HIGH, not close. Always spec a custom RollingMaxIndicator for 52H-style signals: window param, source_column="close", output_column e.g. "rolling_max_252".

---
date: 2026-04-08
title: Realized volatility requires custom indicator
topic: framework_gaps
---
No std_lib indicator computes annualized realized/historical volatility directly. BollingerBandsIndicator computes rolling std internally but does not expose it as a column. For vol-scaling strategies always spec a custom RealizedVolIndicator: close.pct_change().rolling(window).std() * sqrt(252), with output_column "realized_vol" so BaseStrategy.get_sizing_hints() auto-picks it up for VolatilityTargetSizer.

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
title: VolatilityTargetSizer reads candidate.volatility — must name output column "realized_vol"
topic: constructor_gotchas
---
VolatilityTargetSizer.calculate_shares() reads candidate.volatility, which is populated by BaseStrategy.get_sizing_hints() only when it finds a column named exactly "volatility", "realized_vol", "close_to_close_vol_20", or "parkinson_vol_20" in the row. Custom realized-vol indicators must use one of these column names. "realized_vol" is the cleanest choice — unambiguous and first-priority after "volatility".

---
date: 2026-04-08
title: EarningsBlackoutControl is entry-blocker AND exit-forcer — covers both sides of earnings buffer
topic: translation_patterns
---
EarningsBlackoutControl(days=N) handles both blocking new entries AND force-exiting existing positions within N days of earnings. For AQM-52-style strategies that want "exit 2 days before, re-enter 1 day after", set days=2. The re-entry after earnings is handled by the normal monthly rebalance signal logic, not a separate control.

---
date: 2026-04-08
title: Regime halt / market-state gate always requires a custom RiskControl
topic: framework_gaps
---
No std_lib control implements a market-state / regime halt based on trailing market return or VIX level. These always require a custom RiskControl subclass that reads a regime column from df (e.g., "market_state_regime" produced by a custom indicator) and either blocks entries or forces exits based on it. AdvancedRiskControlTemplate supports regime_column + allowed_long_regimes kwargs — use that as the base class to avoid re-implementing direction/stop logic.

---
date: 2026-04-08
title: FCF conversion / fundamental quality gates require custom indicators fed from external data
topic: framework_gaps
---
The std_lib has no fundamental data indicators (FCF, net income, operating cash flow, short interest). These must be custom indicators that join pre-loaded fundamental DataFrames into the OHLCV pipeline. Spec them as custom indicators with is_custom=true and note that the coding agent must handle point-in-time data construction with a 45-day filing lag to avoid look-ahead bias.

