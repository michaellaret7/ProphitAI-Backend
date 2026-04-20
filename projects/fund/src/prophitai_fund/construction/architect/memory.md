---
date: 2026-04-08
title: Cross-sectional ranking is not supported per-ticker — simplify to absolute thresholds
topic: framework_gaps
---
The framework processes each ticker independently; there is no cross-sectional groupby available at indicator or signal time. Ideas requiring sector-neutral ranking (e.g. top-quintile within GICS sector) must be simplified: either precompute sector-relative percentile thresholds offline and pass them in as config parameters, or use an absolute threshold (e.g. composite_score >= 0.60). Document this simplification in implementation_notes every time.

---
date: 2026-04-08
title: RateOfChangeIndicator defaults — always set output_column when multi-instanced
topic: constructor_gotchas
---
RateOfChangeIndicator defaults are window=20, skip_recent=0, output_column=f"roc_{window}". For 6-month momentum use window=126; for standard 12-1 month academic momentum use window=252, skip_recent=21. Always set output_column explicitly when using multiple ROC instances to avoid name collisions (e.g. output_column="roc_126" and output_column="roc_252").

---
date: 2026-04-08
title: VolatilityTargetSizer reads candidate.volatility — use std_lib RealizedVolIndicator
topic: constructor_gotchas
---
VolatilityTargetSizer.calculate_shares() reads candidate.volatility, which is populated by BaseStrategy.get_sizing_hints() only when it finds a column named exactly 'volatility', 'realized_vol', 'close_to_close_vol_20', or 'parkinson_vol_20' in the row. The std_lib RealizedVolIndicator (registry key 'realized_vol') defaults to output_column='realized_vol' and is auto-detected. Use it instead of speccing a custom indicator.

---
date: 2026-04-08
title: EarningsBlackoutControl handles both entry block and forced exit
topic: translation_patterns
---
EarningsBlackoutControl(days=N) handles both blocking new entries AND force-exiting existing positions within N days of earnings. For strategies that want 'exit N days before, re-enter 1 day after', set days=N. Re-entry after earnings is handled by the normal rebalance signal logic, not by a separate control. Only use EarningsBlackoutControl for strategies that want to AVOID holding through earnings; for strategies where earnings proximity IS the entry trigger (pre-earnings attention), spec a custom control instead.

---
date: 2026-04-08
title: Fundamental quality gates require custom indicators fed from external data
topic: framework_gaps
---
The std_lib has no fundamental-data indicators (FCF, net income, operating cash flow, short interest, book value). These must be custom indicators that join pre-loaded fundamental DataFrames into the OHLCV pipeline. Spec them as custom indicators with is_custom=true. The coding agent must handle point-in-time construction with a 45-day filing lag to avoid look-ahead bias.

---
date: 2026-04-13
title: Fundamental-trajectory strategies require all-custom indicator pipeline
topic: framework_gaps
---
Strategies whose alpha signals derive entirely from quarterly financial statement ratios (DuPont decomposition, CCC, FCF conversion, earnings quality) have zero overlap with the std_lib indicator set, which is entirely price/volume based. Every indicator must be is_custom=true. The coding agent must (1) accept pre-loaded fundamental DataFrames keyed by ticker+fiscal_quarter, (2) apply a 45-day filing lag to prevent look-ahead bias, (3) compute TTM aggregates by summing four most recent quarters for flow items and averaging for balance sheet items, (4) output scalar columns per row into the OHLCV pipeline. Always add an implementation_note stating that all fundamental columns arrive via a pre-joined fundamental pipeline, not from OHLCV data.

---
date: 2026-04-13
title: Sector-neutral z-scores in per-ticker architecture — simplification options
topic: translation_patterns
---
Strategies that call for cross-sectional sector-neutral z-score ranking need simplification since the framework has no groupby. Two valid approaches: (1) precompute sector percentile thresholds offline (historical distributions), store as rolling reference values keyed by sector+date, join to each ticker row so the signal compares abs(composite_score) >= precomputed_80th_pct_threshold; (2) use absolute z-score thresholds (e.g. composite >= 0.50 for long, <= -0.50 for short) as initial conservative defaults, documented in implementation_notes. The composite score itself can be computed per-ticker when it's a weighted sum of already-normalized inputs.

---
date: 2026-04-13
title: Quarterly-rebalance strategies need large min_bars_required buffer for fundamental lag
topic: constructor_gotchas
---
Strategies requiring N quarters of financial history plus a 45-day filing lag need min_bars_required of at least (N * 63) + buffer trading days. For 10-quarter lookbacks this is 630+ bars. Realized vol (window=126) and 10Y yield guard (window=63) fit within this buffer. Always set min_bars_required >= max(fundamental_lookback_in_trading_days, indicator_warmup_bars). For fundamental strategies this is the fundamental lookback, not the price indicator warmup.

---
date: 2026-04-14
title: Second-derivative signals: row-wise std across quarter columns
topic: translation_patterns
---
When translating second-derivative signals (change-in-growth-rate normalized by volatility of growth rates), the std is computed across the N quarterly values in the same row (pandas axis=1 std), NOT a rolling window along the time axis. This captures cross-quarter dispersion within the current snapshot. Floor the std at 0.001 to prevent division by zero. Pattern: signal_raw = (value_q0 - value_qN) / max(row_std([value_q0..qN]), 0.001).

---
date: 2026-04-14
title: Quarterly fundamental indicators output N separate columns (q0..qN), not a single series
topic: translation_patterns
---
Strategies using quarterly fundamental data (revenue, margins, balance-sheet items) should spec custom indicators that output each quarter as a separate column (revenue_q0, revenue_q1, ..., revenue_q8). This keeps all derived-feature math expressible as row-wise pandas operations on the OHLCV DataFrame, avoids multi-index or lag operations in derived features, and makes the pipeline sequentially valid. The indicator job is join + forward-fill columns; the derived features handle the math.

---
date: 2026-04-14
title: Sector concentration control is always custom — no std_lib equivalent
topic: framework_gaps
---
No std_lib risk control handles sector concentration caps. Always spec a custom SectorConcentrationControl that (1) reads a pre-loaded ticker-to-GICS-sector mapping, (2) computes current sector gross exposure from PortfolioTracker, (3) blocks new entries when sector exceeds max_sector_gross_pct. Implement only should_block_entry (not should_force_exit) since trimming existing positions is operationally complex.

---
date: 2026-04-14
title: VIX regime gate two-layer pattern: signal condition + risk control backstop
topic: translation_patterns
---
For VIX-scaled exposure strategies, use a two-component pattern: (1) a custom MacroRegimeIndicator outputs both vix_level (smoothed 5-day avg) and vix_regime_scale (step-function scalar: 1.0/0.85/0.65/0.0 based on VIX bands); (2) vix_regime_scale is referenced directly in long_entry/short_entry signal conditions (vix_regime_scale > 0.0) AND passed to the custom sizer via get_sizing_hints() for continuous scaling. A separate VixRegimeGateControl reads vix_level directly as a redundant hard stop. The signal condition is the primary gate; the risk control is the backstop.

---
date: 2026-04-14
title: Signal-model exits with multiple triggers use OR logic — always document explicitly
topic: translation_patterns
---
When a strategy has multiple independent exit triggers (scheduled rebalance fall-off, signal reversal, regime halt, hard stop, time stop), long_exit and short_exit conditions in the manifest represent OR logic — any single condition triggers exit. Always add an implementation_note titled 'Long exit logic — ANY condition triggers exit' to make this explicit, since the coding agent may default to AND logic. StopLossExitControl and TimeStopControl handle price-based and time-based exits outside the signal model.

---
date: 2026-04-14
title: Fundamental strategies need a dedicated UniverseFilter in wiring.py
topic: framework_gaps
---
Strategies with complex universe criteria (market cap bands, ADV thresholds, sector exclusions, SPAC/BDC exclusions, short interest, SBC/SGA ratios) cannot implement these filters in the per-ticker indicator pipeline. Always add an implementation_note documenting that a UniverseFilter class must be built in wiring.py (or a separate universe builder) that runs before tickers are passed to the strategy engine. The indicator pipeline only receives pre-filtered tickers.

---
date: 2026-04-14
title: Multi-snapshot balance-sheet strategies: spec separate columns at every lag
topic: translation_patterns
---
Strategies computing sequential quarter-over-quarter deltas (e.g. q0 vs q2 vs q4) need balance sheet snapshots at EVERY lag used — not just current and year-ago. The custom fundamental indicator must be specced to output the balance-sheet item at each required snapshot (e.g. receivables_q2, inventory_q2, payables_q2) plus matching TTM denominators (revenue_ttm_q2, cogs_ttm_q2 derived from flow items q2..q5). Always enumerate every snapshot in the indicator spec.

---
date: 2026-04-14
title: Exit conditions must compare change-columns to 0 and level-columns to absolute thresholds
topic: process_mistakes
---
Common error: exit condition written as 'spread_change_yoy < spread_q4', which compares a change value to a level value. Correct form is 'spread_change_yoy < 0.0' (change is negative → spread compressed vs year-ago). Always double-check that exit conditions compare change-columns to 0 and level-columns to absolute thresholds — never mix change and level in a single inequality.

---
date: 2026-04-14
title: UnemploymentRegimeControl pattern for macro time-series threshold counting
topic: framework_gaps
---
Strategies with recession triggers based on consecutive weeks of elevated macro time series (initial claims, ISM, NFP) require a custom control that (1) reads the macro column broadcast by a MacroRegimeIndicator (weekly interpolated to daily), (2) counts consecutive weeks exceeding threshold, (3) blocks new entries after N consecutive triggering weeks, (4) resets counter when the series falls back below threshold for 2+ weeks. No std_lib equivalent. Implement as entry-blocker only (should_block_entry returns True, should_force_exit returns False). Pattern reusable for any macro time-series threshold trigger.

---
date: 2026-04-16
title: Rolling OLS alpha strategies: InformationRatio must be a separate downstream indicator
topic: translation_patterns
---
For residual-momentum strategies that compute Information Ratio = alpha / residual_std, the ResidualAlphaIndicator must output BOTH alpha_vs_spy AND residual_std as separate columns. InformationRatioIndicator is a separate downstream indicator in the pipeline that reads those two columns as input_columns. Do NOT compute IR inside ResidualAlphaIndicator — the derived composite needs IR as an independent column for z-scoring weight. Indicator ordering: RealizedVol → MacroRegime → ResidualAlpha → SectorResidualAlpha → InformationRatio → ADX → 52WkHigh → RiskAdjMomentum.

---
date: 2026-04-16
title: Composite score normalization: clip-and-rescale to [0,1] for sizer compatibility
topic: translation_patterns
---
When a strategy's entry signal is a weighted composite of z-scored inputs (composite = 0.4*z1 + 0.4*z2 + 0.2*z3), the raw composite is approximately N(0, ~1) and can be negative. For sizer compatibility (candidate.score is expected in [0,1]), normalize via clip to [-3, 3] then rescale to [0,1] as (clipped + 3.0) / 6.0. Entry threshold 0.60 on this scale corresponds to a raw z-composite of +0.60, approximately the 75th percentile of N(0,1). Document both raw and normalized forms in derived_feature logic and implementation_notes.

---
date: 2026-04-16
title: Three-layer sizer chain: VolTarget → DrawdownScaled → custom RegimeScaled outer
topic: translation_patterns
---
For strategies with multiple simultaneous sizing axes (vol-target base + drawdown scaling + regime scaling), use a three-layer chain: VolatilityTargetSizer(max_pct_equity=X) as the base, wrapped by DrawdownScaledSizer, with a custom outer sizer that delegates to DrawdownScaledSizer for the base share count then multiplies by regime scale factors from candidate sizing hints. The custom outer reads regime scales (vix_regime_scale, market_state_scale) from hints populated by get_sizing_hints(). Declare these in strategy_class.sizing_hints as value_str references to column names, not value_num.

---
date: 2026-04-16
title: Side-differentiated stops require custom control — StopLossExitControl is direction-neutral
topic: framework_gaps
---
StopLossExitControl applies the same pct threshold to both LONG and SHORT positions regardless of direction. For strategies needing different stop percentages by side (e.g. -10% on longs for drawdown, +18% on shorts for squeeze protection), spec a custom control that in should_force_exit() checks position.direction and applies separate thresholds. Pattern: SHORT gets the wider squeeze stop, LONG gets the tighter drawdown stop. Returns False from should_block_entry().

---
date: 2026-04-16
title: Asymmetric halt pattern: force-exit shorts, block all entries, hold longs
topic: translation_patterns
---
For long/short strategies with funding-stress or panic-VIX halts, the correct asymmetric pattern is (1) force-exit ALL short positions immediately (right-tail squeeze risk), (2) block ALL new entries (long and short), (3) do NOT force-exit existing longs (quality names may benefit from flight-to-quality during stress). Implement as separate custom controls with force_exit_shorts_on_halt=True and only-block-entries for longs. No std_lib equivalent handles side-differentiated force-exit. Also mirror halt columns as signal conditions (halt_active == 0.0 in entry conditions) as defense-in-depth.

---
date: 2026-04-16
title: Price-path signals — combine all metrics into a single custom indicator
topic: translation_patterns
---
For strategies whose signals are all price-path-derived (FIP fraction, equity_curve_r2, autocorrelation, zero-return pct, rolling momentum), spec a single custom indicator that outputs all metrics from the 'close' column in one rolling-window pass. This avoids multiple custom indicator files and keeps warmup arithmetic simple. If momentum-skip is 252 lookback + 21 skip, min_bars_required = 273 + ~42 buffer = 315 to allow z-score rolling windows to stabilize. Place AFTER RealizedVolIndicator in the pipeline when risk_adj_momentum = momentum / realized_vol depends on its output.

---
date: 2026-04-16
title: Monthly-rebalance scheduling: signal model must gate entry and E1 on is_rebalance_bar()
topic: translation_patterns
---
For monthly-rebalance strategies with daily signal models, entry signals AND the scheduled E1 exit (composite below median) must be gated behind a helper method is_rebalance_bar(timestamp) returning True only in the first 2 trading days of a new calendar month. Mid-month intraday exits (signal decay, reversal, VIX/regime flags) fire on ANY bar. Document this per-condition scheduling in implementation_notes; coding agents default to evaluating all conditions uniformly.

---
date: 2026-04-16
title: Sustained-halt pattern: rolling_min over N days is simpler than stateful counter
topic: translation_patterns
---
For 'X > threshold sustained N days' patterns, the calculation spec should use pandas rolling_min(N)(x_level) > threshold rather than a stateful day-counter loop. This is fully vectorizable and avoids state management in the indicator. Example: vix_entry_halt = (rolling_min(5)(vix_level) > 35.0).astype(float). Specify the exact formula in the calculation field so the coding agent doesn't implement a slow Python loop.

---
date: 2026-04-17
title: Event-driven strategies: days_since_event is iterative, not vectorizable
topic: translation_patterns
---
For strategies where entry eligibility and exit conditions depend on the count of trading days since a specific event (earnings, macro release, corporate action), days_since_event cannot be computed as a rolling window — it must reset to 0 on each event date and increment daily. This requires row-by-row iteration in the custom indicator, not a vectorized pandas operation. Always add an implementation_note flagging this. State management pattern: 'if event_date on this bar → set=0; else → previous_value + 1; forward-fill event-anchor columns (event_date, event_metrics) until the next event.'

---
date: 2026-04-17
title: VIX-conditional entry: separate vix_regime_gate and vix_panic_halt columns
topic: translation_patterns
---
For mean-reversion strategies with a VIX range gate (e.g. VIX 18-45 sweet spot), use TWO separate columns from the macro regime indicator: (1) vix_regime_gate = 1.0 when VIX is within the valid trading range (both floor and ceiling); (2) vix_panic_halt = 1.0 when VIX exceeds panic threshold for N consecutive days using rolling_min(N)(vix_level) > threshold. Do NOT collapse these — vix_regime_gate gates entry, vix_panic_halt triggers force-exits. This differs from momentum/factor strategies where a single vix_regime_scale scalar suffices. For VIX-gated mean-reversion, vix_sizing_scale can be a piecewise linear column (1.0 in sweet spot, tapering at edges) embedded into the entry score via multiplication in derived_features rather than a custom outer sizer — simplifies the sizer chain to 2 layers.

---
date: 2026-04-17
title: Rolling percentile rank for own-history oversold detection
topic: translation_patterns
---
For strategies using per-ticker own-history percentile thresholds (e.g. RSI in bottom quintile of its own trailing 252-day distribution), the correct vectorized pandas pattern is df['rsi'].rolling(window=252).rank(pct=True) * 100. Output is NaN for the first window-1 bars. During warmup, fill NaN with 50.0 (neutral percentile) in derived_features to prevent NaN propagation into the composite score. This pattern avoids cross-sectional ranking — each ticker ranks only against its own history, compatible with the per-ticker architecture. Also applies to rolling-rank of cumulative returns and Bollinger bandwidth.

---
date: 2026-04-17
title: SPY broad-market gate for ETF strategies: include SPY in universe, broadcast its columns
topic: translation_patterns
---
For ETF mean-reversion strategies that gate entries on SPY's own 200-day SMA and 20-day return, include SPY as a ticker in the universe (not as external macro data). In the indicator suite's calculate() method, after running per-ticker indicators, extract SPY's sma_200, close-vs-sma_200, and pct_change(20) as universe-scoped columns and broadcast them (by date-index join) into every other ticker's DataFrame as spy_above_200sma, spy_20d_return, and broad_market_gate. SPY's own DataFrame gets broad_market_gate set from its own values. The macro regime indicator should be specified as scope='universe' to signal this broadcast pattern. Architecturally identical to the VIX broadcast pattern but uses a universe ticker instead of an external data feed.

---
date: 2026-04-17
title: Pre-earnings event strategies: economic_calendar data_requirement + custom pre-exit control
topic: translation_patterns
---
For strategies where the ENTRY trigger depends on forward earnings proximity rather than a blackout: (1) Do NOT use EarningsBlackoutControl — it blocks entries and force-exits within N days of earnings, the opposite of what a pre-earnings strategy needs. Spec a custom control that force-exits when days_to_earnings <= 1 and blocks entries when NOT in the entry window. (2) Use data_requirements kind='economic_calendar' with attrs_key='earnings_calendar', scope='per_ticker', params={'country': 'US', 'event': 'earnings'}. (3) days_to_earnings is iterative (not vectorizable) — decrement each bar from the forward count at anchor date; reset when a new announcement date appears. Fill pre-calendar NaN with 999.

---
date: 2026-04-17
title: Event-anchored rolling ratio: forward-fill from event date until next event
topic: translation_patterns
---
For strategies computing attention proxies based on prior-event rolling ratios (e.g. announcement_vol_ratio = avg volume in 5-bar window around prior earnings / rolling 252-bar baseline volume), the indicator must (1) depend on days_since_prior_event from the calendar indicator, (2) iterate bar-by-bar: at each bar where days_since_prior_event == 0, compute the window ratio and store it, (3) forward-fill the ratio until the next event, (4) fill pre-first-event with 1.0. Cannot be vectorized. Declare this dependency by ordering the attention-metric indicator AFTER the event-calendar indicator in the indicators list.
---
date: 2026-04-17
title: Pure-TTM-ratio strategies: financial_ratios data_requirement covers all pre-computed TTM fields
topic: translation_patterns
---
For strategies whose composite is built entirely from pre-computed TTM ratios (dividend yield, FCF yield, coverage ratios, debt ratios), use data_requirement kind='financial_ratios' (scope='per_ticker') — no need to also request kind='fundamentals' and compute TTM aggregates manually. The financial_ratios feed exposes columns like dividendYieldTTM, priceToFreeCashFlowsRatioTTM, dividendPaidAndCapexCoverageRatioTTM, debtRatioTTM, interestCoverageTTM directly. This avoids speccing the q0..q3 quarterly snapshot pattern. FCF yield = 1.0 / priceToFreeCashFlowsRatioTTM (clip at [0,1], set 0 if denominator <= 0). Always apply 45-day filing lag via point-in-time join in the custom indicator.

---
date: 2026-04-17
title: financial_ratios feed covers TTM efficiency ratios; fundamentals needed for raw EBIT/revenue history
topic: translation_patterns
---
For fundamental quality strategies combining LEVEL ratios (asset turnover, gross margin, ROA, ROCE) with TREND metrics (YoY margin change, multi-year ROCE change, EBIT vs revenue CAGR): the financial_ratios feed (kind='financial_ratios') covers all level TTM ratios directly (assetTurnoverTTM, grossProfitMarginTTM, returnOnAssetsTTM, returnOnCapitalEmployedTTM, operatingProfitMarginTTM). However, multi-year trend metrics that require looking back N quarters of the same TTM value (e.g. ROCE change 5yr = ROCE[t] - ROCE[t-20Q]) need the financial_ratios at EARLIER quarter lags — this is achievable by fetching additional lagged snapshots. EBIT growth YoY and revenue CAGR require raw quarterly income statement line items — these live in kind='fundamentals'. Always spec both data_requirements when the trend component needs raw EBIT/revenue. Two separate custom indicators (LevelIndicator + TrendIndicator) is cleaner than one indicator with 10 output columns — keeps calculation description manageable.

---
date: 2026-04-17
title: Equal-weight strategies: PercentOfEquitySizer cannot be truly equal-weight — flag for dynamic override
topic: framework_gaps
---
PercentOfEquitySizer uses a static pct parameter. For truly equal-weight strategies (pct = 1/current_position_count, capped at max_name_pct), the static pct cannot adapt as positions open/close. Always add an implementation_note 'Equal-weight sizing: PercentOfEquitySizer pct must be dynamically computed' instructing the coding agent to implement a thin EqualWeightPositionSizer or wiring.py override that computes pct = min(1.0 / max(context.open_position_count, 1), max_name_pct) at calculate_shares() time. This is the correct pattern for any 50-120 name equal-weight portfolio targeting 95-100% deployment.

---
date: 2026-04-20
title: Cross-sectional dispersion uses universe_returns data_requirement
topic: translation_patterns
---
For strategies whose regime gate depends on cross-sectional dispersion (std of universe returns across tickers), declare `DataRequirement(kind="universe_returns", attrs_key="universe_returns", scope="shared")` on the dispersion indicator. The resolver attaches a DataFrame (date × ticker) of daily returns to every ticker's `df.attrs["universe_returns"]`. The indicator reads `df.attrs["universe_returns"]` and computes `universe_returns.std(axis=1).rolling(21).mean()`. DO NOT override `suite.calculate()` to pre-inject — the vectorized engine never calls such an override path.

---
date: 2026-04-20
title: Rolling OLS residual alpha: separate indicators for SPY-alpha and sector-alpha, IR downstream
topic: translation_patterns
---
For residual-reversal strategies built on rolling OLS regressions vs market and sector: (1) ResidualAlphaIndicator outputs alpha_vs_spy, beta_vs_spy, residual_std_spy (annualized) reading `df.attrs['spy']` from a `DataRequirement(kind="equity_price", attrs_key="spy", scope="shared", params={"symbol": "SPY"})`; (2) SectorResidualAlphaIndicator reads `df.attrs['ticker_meta']['sector']` (platform-provided dict) to map to ETF proxy and outputs alpha_vs_sector, residual_std_sector — one `DataRequirement(kind="equity_price", ...)` per sector ETF (XLK, XLV, XLF, XLE, XLY, XLP, XLI, XLU, XLB, XLRE, XLC); (3) InformationRatioIndicator = alpha_vs_spy / max(residual_std_spy, 0.001), MUST come after ResidualAlphaIndicator. Composite reversal score = -1 * (z_alpha_spy + z_alpha_sector + z_IR), where each z is own-history rolling 63-day z-score. Normalization: clip(-4.5, 4.5) then rescale to [0,1] via (x+4.5)/9.0. Sector ETF mapping is a hardcoded dict in SectorResidualAlphaIndicator keyed by GICS sector name.

---
date: 2026-04-20
title: Three new data_requirement kinds — equity_price, ticker_meta dict, universe_returns
topic: framework_gotchas
---
Architect may specify three platform-native kinds: (a) `kind="equity_price"` params={"symbol": "SPY"} scope="shared" — ETF/equity close series (replaces commodity misuse for SPY/sector ETFs). One DataRequirement per symbol; attaches tz-naive `pd.Series` to `df.attrs[attrs_key]`. (b) `kind="ticker_meta"` scope="per_ticker" — attaches dict `{"symbol","sector","industry"}` to `df.attrs[attrs_key]`. Recommended attrs_key="ticker_meta". Sector-proxy indicators read `meta["sector"]`. (c) `kind="universe_returns"` scope="shared" optional params={"return_type": "pct"|"log"} — cross-sectional returns DataFrame (date × ticker) at `df.attrs[attrs_key]`. Used for dispersion regimes and universe-relative features. Indicator agents should never be told to override `suite.calculate()` to pre-inject these — declare the data_requirement and the resolver handles it.

---
date: 2026-04-20
title: Daniel-Moskowitz panic-state indicator: bear mean-variance requires conditional forward-fill
topic: translation_patterns
---
For PanicRegimeIndicator (Daniel-Moskowitz 2016), spx_mean_bear_variance = rolling mean of realized variance computed ONLY over bear-period bars, then forward-filled to all bars. If the backtest period never enters a bear state, fall back to unconditional rolling(252).mean() of variance to prevent division-by-zero in panic_intensity. Pattern: bear_var_series = spx_realized_variance_126d.where(spx_bear_indicator == 1.0, np.nan).rolling(252, min_periods=1).mean().ffill().fillna(spx_realized_variance_126d.rolling(252, min_periods=1).mean()). This handles cold-start and all-bull backtests gracefully.

---
date: 2026-04-20
title: FIP rolling apply is slow — recommend numba or fixed threshold
topic: framework_gaps
---
Frog-In-Pan (Da-Gurun-Warachka 2014) requires counting direction-concordant small returns in each trailing 252-bar window. This is a per-row apply over O(252) elements for each of 400-700 tickers × 3000+ bars — extremely slow with Python rolling apply. Always flag in implementation_notes: use numba JIT or pre-compute with vectorized numpy (threshold = scalar from most recent realized_vol, not per-bar dynamic threshold) to achieve acceptable backtest performance. Fallback: use fixed threshold |r| < 0.01 instead of 0.5 * realized_vol for 10-100x speedup.

---
date: 2026-04-20
title: PanicHaltControl: direction-differentiated force-exit for long-short asymmetric halt
topic: translation_patterns
---
For Daniel-Moskowitz zero-gross-on-panic strategies, the asymmetric halt pattern is: PanicHaltControl.should_force_exit() checks position.direction — force-exit SHORTS immediately (right-tail squeeze risk), do NOT force-exit LONGS (flight-to-quality hold). should_block_entry() returns True for ALL new entries regardless of direction. Signal model ALSO gates entries on panic_state_gate == 1.0 as defense-in-depth (defense-in-depth pattern: both signal condition AND risk control enforce the same rule). Custom outer sizer also scales all new shares to 0 via panic_exposure_scale == 0.0 — triple redundancy. This triple-lock pattern (signal gate + risk control + sizer) is appropriate for the primary risk failure mode of a long-short momentum strategy.

