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

---
date: 2026-04-13
title: DuPont / fundamental decomposition strategies require all-custom indicator pipeline
topic: framework_gaps
---
Strategies whose alpha signals derive entirely from quarterly financial statement ratios (NPM, Asset Turnover, Equity Multiplier, ROE) have zero overlap with the std_lib indicator set, which is entirely price/volume based. Every indicator must be is_custom:true. The coding agent must: (1) accept pre-loaded fundamental DataFrames keyed by ticker+fiscal_quarter, (2) apply a 45-day filing lag to prevent look-ahead bias, (3) compute TTM aggregates by summing four most recent quarters for flow items and averaging for balance sheet items, (4) output scalar columns per row into the OHLCV pipeline. Document in implementation_notes that all fundamental columns arrive via a pre-joined fundamental data pipeline, not from OHLCV data.

---
date: 2026-04-13
title: Sector-neutral z-scores in per-ticker architecture — simplification pattern
topic: translation_patterns
---
DuPont-style strategies call for cross-sectional sector-neutral z-score ranking (e.g., "top quintile within GICS sector"). The framework processes each ticker independently with no groupby. Simplification: precompute sector percentile thresholds offline (e.g., using historical distributions), store them as rolling reference values in a separate reference DataFrame keyed by sector+date, then join to each ticker row so the signal can compare abs(DQS) >= precomputed_80th_pct_threshold. Alternatively, use absolute z-score thresholds (e.g., composite_dqs >= 0.50 for long, <= -0.50 for short) as initial conservative defaults, documented in implementation_notes. The composite DQS score itself can be computed per-ticker since it is a weighted sum of already-normalized inputs.

---
date: 2026-04-13
title: Quarterly-rebalance strategies need large min_bars_required buffer for fundamental lag
topic: constructor_gotchas
---
Strategies requiring 10+ quarters of financial history plus a 45-day filing lag need a min_bars_required of at least 630 bars (10 quarters × ~63 trading days). Also, the realized vol indicator for 6-month vol scaling (window=126) and the 10Y yield change guard (window=63) are well within this buffer. Always set min_bars_required >= max(fundamental_lookback_in_trading_days, indicator_warmup_bars) — for DuPont-style strategies this is the fundamental lookback, not the price indicator warmup.

---
date: 2026-04-14
title: RAS second-derivative: row-wise std across quarter columns, not rolling time-series std
topic: translation_patterns
---
When translating second-derivative revenue signals (change-in-growth-rate normalized by volatility of growth rates), the std is computed across the 4 quarterly YoY growth rate values in the same row (pandas axis=1 std), NOT a rolling window along the time axis. This captures cross-quarter dispersion within the current snapshot. Floor the std at 0.001 to prevent division by zero. The formula becomes: ras_raw = (yoy_growth_q0 - yoy_growth_q3) / max(row_std([yoy_growth_q0..q3]), 0.001).

---
date: 2026-04-14
title: Quarterly fundamental indicators output N separate columns (q0..qN), not a single series
topic: translation_patterns
---
Strategies using quarterly fundamental data (revenue, SG&A, D&A, gross profit) should spec custom indicators that output each quarter as a separate column (revenue_q0, revenue_q1, ..., revenue_q8). This pattern keeps all derived feature math expressible as row-wise pandas operations on the OHLCV DataFrame, avoids the need for multi-index or lag operations in derived features, and makes the pipeline sequentially valid. The indicator job is just to join + forward-fill the columns; the derived features handle the math.

---
date: 2026-04-14
title: Sector concentration control is always custom — no std_lib equivalent
topic: framework_gaps
---
No std_lib risk control handles sector concentration caps. Must always spec a custom SectorConcentrationControl that: (1) reads a pre-loaded ticker-to-GICS-sector mapping, (2) computes current sector gross exposure from PortfolioTracker, (3) blocks new entries when sector exceeds max_sector_gross_pct. Should only implement should_block_entry (not should_force_exit) since trimming existing positions is operationally complex in the current framework.

---
date: 2026-04-14
title: VIX regime gate: two-layer pattern — MacroRegimeIndicator produces vix_regime_scale column, VixRegimeGateControl reads it
topic: translation_patterns
---
For VIX-scaled exposure strategies, use a two-component pattern: (1) Custom MacroRegimeIndicator outputs both vix_level (smoothed 5-day avg) and vix_regime_scale (step-function scalar: 1.0/0.85/0.65/0.0 based on VIX bands). (2) vix_regime_scale is referenced directly in long_entry/short_entry signal conditions (vix_regime_scale > 0.0) AND passed to the custom sizer via get_sizing_hints() for continuous scaling. A separate VixRegimeGateControl also reads vix_level directly as a redundant hard stop. The signal condition is the primary gate; the risk control is the backstop.

---
date: 2026-04-14
title: Long exit OR logic must be explicit in implementation_notes
topic: translation_patterns
---
When a strategy has multiple independent exit triggers (scheduled rebalance fall-off, RAS inflection reversal, GMT deterioration, hard stop, time stop), the signal model long_exit and short_exit conditions in the manifest represent OR logic — any single condition triggers exit. Always add an implementation_note titled 'Long exit logic — ANY condition triggers exit' to make this explicit, since the coding agent might default to AND logic if not instructed. StopLossExitControl and TimeStopControl handle the price-based and time-based exits outside the signal model.

---
date: 2026-04-14
title: Fundamental strategies need a dedicated UniverseFilter in wiring.py
topic: framework_gaps
---
Strategies with complex universe criteria (market cap bands, ADV thresholds, sector exclusions, SPAC/BDC exclusions, short interest checks, SBC/SGA ratios for specific sectors) cannot implement these filters in the per-ticker indicator pipeline. Always add an implementation_note documenting that a UniverseFilter class must be built in wiring.py or a separate universe builder that runs before tickers are passed to the strategy engine. The indicator pipeline only receives pre-filtered tickers.

